from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
)
from textual import on

from kissaten.dedup import storage


class RegionListItem(ListItem):
    """ListItem that holds region data."""

    def __init__(self, label: str, country: str, slug: str):
        super().__init__(Label(label))
        self.region_data = (country, slug)


class RegionScreen(Screen):
    """Screen for selecting a region to process."""

    BINDINGS = [("escape", "quit", "Quit")]

    def __init__(self, country_code: str | None = None):
        super().__init__()
        self.country_code = country_code

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Select a Region to Process", classes="title"),
            Input(placeholder="Search regions...", id="region_search"),
            ListView(id="region_list"),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Load regions on mount."""
        self.regions = storage.get_all_regions(self.country_code)
        self.update_list(self.regions)
        self.query_one("#region_search").focus()

    def update_list(self, regions) -> None:
        """Update the region list view."""
        list_view = self.query_one("#region_list")
        list_view.clear()
        for country, name, slug in regions:
            label = f"{country} - {name} ({slug})"
            # Use custom ListItem to store data safely, no ID packing needed
            list_view.append(RegionListItem(label, country, slug))

    @on(Input.Changed, "#region_search")
    def filter_regions(self, event: Input.Changed) -> None:
        """Filter regions based on search input."""
        query = event.value.lower()
        filtered = [r for r in self.regions if query in r[0].lower() or query in r[1].lower() or query in r[2].lower()]
        self.update_list(filtered)

    @on(ListView.Selected, "#region_list")
    def select_region(self, event: ListView.Selected) -> None:
        """Handle region selection."""
        if isinstance(event.item, RegionListItem):
            country, composite_slug = event.item.region_data
            # Extract actual slug from composite key (Country:Slug)
            slug = composite_slug.split(":")[1] if ":" in composite_slug else composite_slug
            self.app.push_screen(FarmDedupScreen(country, slug))


class FarmDedupScreen(Screen):
    """Screen for manual farm deduplication."""

    BINDINGS = [
        ("escape", "back", "Back to Regions"),
        ("space", "toggle_selection", "Select/Deselect"),
        ("m", "merge", "Merge Selected"),
        ("s", "save", "Save Changes"),
    ]

    def __init__(self, country: str, region_slug: str):
        super().__init__()
        self.country = country
        self.region_slug = region_slug
        # Load clusters from mappings + current DB state
        self.clusters = storage.rehydrate_clusters_from_mappings(country, region_slug)
        self.farms = storage.get_farms_for_region(country, region_slug)
        self.selected_rows = set()  # Set of safe row keys
        self._row_key_map = {}  # Maps safe_key -> real identifier string

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label(f"Processing: {self.country} - {self.region_slug}", classes="subtitle"),
            Input(placeholder="Search farms...", id="farm_search"),
            DataTable(id="farm_table"),
            Horizontal(
                Button("Merge Selected (m)", variant="primary", id="btn_merge"),
                Button("Save and Exit (s)", variant="success", id="btn_save"),
                classes="actions",
            ),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize table."""
        table = self.query_one(DataTable)
        table.add_column("Select", key="select")
        table.add_column("Farm Name", key="farm_name")
        table.add_column("Normalized", key="normalized")
        table.add_column("Producer", key="producer")
        table.add_column("Beans", key="beans")
        table.cursor_type = "row"
        self.load_table_data()

    def load_table_data(self, query: str = "") -> None:
        """Populate table with farms."""
        table = self.query_one(DataTable)
        table.clear()
        self.selected_rows.clear()
        self._row_key_map.clear()

        # 1. Add existing clusters
        for i, cluster in enumerate(self.clusters):
            name = f"[bold]{cluster['canonical_name']}[/bold] (Cluster)"
            if query and query not in name.lower():
                continue

            real_id = f"cluster:{cluster['canonical_name']}"
            safe_key = f"c_{i}"  # Simple safe key
            self._row_key_map[safe_key] = real_id

            table.add_row(
                "☐", name, f"{len(cluster['entries'])} entries", "", str(cluster["total_bean_count"]), key=safe_key
            )

        # 2. Add unclustered farms
        # Filter out farms that are already in clusters
        clustered_normalized_names = set()
        for c in self.clusters:
            for entry in c["entries"]:
                clustered_normalized_names.add(entry["farm_normalized"])

        idx = 0
        for normalized, entries in self.farms.items():
            if normalized in clustered_normalized_names:
                continue

            first = entries[0]
            display_name = first["farm_name"]

            if query and query not in display_name.lower():
                continue

            real_id = f"farm:{normalized}"
            safe_key = f"f_{idx}"
            self._row_key_map[safe_key] = real_id
            idx += 1

            table.add_row(
                "☐",
                display_name,
                normalized,
                first["producer_name"],
                str(sum(e["bean_count"] for e in entries)),
                key=safe_key,
            )

    @on(Input.Changed, "#farm_search")
    def on_search(self, event: Input.Changed) -> None:
        self.load_table_data(event.value.lower())

    def action_toggle_selection(self) -> None:
        """Toggle selection of current row."""
        table = self.query_one(DataTable)
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        except Exception:
            # Handle case where table is empty or cursor invalid
            return

        if row_key in self.selected_rows:
            self.selected_rows.remove(row_key)
            icon = "☐"
        else:
            self.selected_rows.add(row_key)
            icon = "☑"

        table.update_cell(row_key, "select", icon)

    def action_merge(self) -> None:
        """Merge selected items."""
        if len(self.selected_rows) < 2:
            self.notify("Select at least 2 items to merge", severity="warning")
            return

        # Determine default name (longest)
        selected_names = []
        for safe_key in self.selected_rows:
            real_id = self._row_key_map.get(safe_key)
            if not real_id:
                continue

            # Parse key to identify source
            type_, id_ = real_id.split(":", 1)
            if type_ == "cluster":
                selected_names.append(id_)
            elif type_ == "farm":
                # Find display name for this normalized key
                entries = self.farms.get(id_, [])
                if entries:
                    selected_names.append(entries[0]["farm_name"])

        default_name = max(selected_names, key=len) if selected_names else ""

        self.app.push_screen(NameInputScreen(default_name), self.complete_merge)

    def complete_merge(self, canonical_name: str | None) -> None:
        """Callback from name input."""
        if not canonical_name:
            return

        new_cluster_entries = []
        total_beans = 0
        confidences = []

        # 1. Identify what to remove
        clusters_to_remove_indices = []

        for safe_key in self.selected_rows:
            real_id = self._row_key_map.get(safe_key)
            if not real_id:
                continue

            type_, id_ = real_id.split(":", 1)

            if type_ == "cluster":
                # Find the cluster index
                for i, c in enumerate(self.clusters):
                    if c["canonical_name"] == id_:
                        clusters_to_remove_indices.append(i)
                        new_cluster_entries.extend(c["entries"])
                        total_beans += c["total_bean_count"]
                        confidences.append(c["confidence"])
                        break

            elif type_ == "farm":
                entries = self.farms.get(id_, [])
                new_cluster_entries.extend(entries)
                total_beans += sum(e["bean_count"] for e in entries)
                confidences.append(1.0)  # Manual merge implies high confidence

        # 2. Update Local Clusters
        self.clusters = [c for i, c in enumerate(self.clusters) if i not in clusters_to_remove_indices]

        # Create new cluster
        new_cluster = {
            "canonical_name": canonical_name,
            "entries": new_cluster_entries,
            "total_bean_count": total_beans,
            "confidence": 1.0,  # Manual
            "country_code": self.country,
            "region_name": self.clusters[0]["region_name"] if self.clusters else "",
            "region_slug": self.region_slug,
        }

        self.clusters.append(new_cluster)

        # 3. Refresh UI
        self.selected_rows.clear()
        self.load_table_data()
        self.notify(f"Merged into '{canonical_name}'")

    def action_save(self) -> None:
        """Save changes to disk."""
        storage.update_region_clusters(self.country, self.region_slug, self.clusters)
        self.notify("Mappings saved!", severity="information")
        self.app.pop_screen()

    def action_back(self) -> None:
        """Go back to region selection."""
        self.app.pop_screen()


class NameInputScreen(Screen):
    """Modal to enter canonical name."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    CSS = """
    NameInputScreen {
        align: center middle;
    }
    Container {
        width: 60;
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 1;
    }
    Label {
        margin-bottom: 1;
    }
    """

    def __init__(self, default_name: str):
        super().__init__()
        self.default_name = default_name

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Enter Canonical Farm Name:"),
            Input(value=self.default_name, id="name_input"),
            Horizontal(
                Button("Cancel", variant="error", id="cancel"),
                Button("Confirm", variant="primary", id="confirm"),
                classes="actions",
            ),
        )

    def on_mount(self) -> None:
        self.query_one("#name_input").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            val = self.query_one("#name_input").value
            self.dismiss(val)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ManualDedupApp(App):
    """Farm Deduplication Manual Review Tool."""

    CSS = """
    .title {
        text-align: center;
        padding: 1;
        background: $primary;
        color: $text;
        text-style: bold;
    }
    .subtitle {
        text-align: center;
        background: $secondary;
        color: $text;
    }
    .actions {
        height: 3;
        align: center middle;
        dock: bottom;
    }
    DataTable {
        height: 1fr;
    }
    """

    def __init__(self, country_code: str | None = None):
        super().__init__()
        self.country_code = country_code

    def on_mount(self) -> None:
        self.push_screen(RegionScreen(self.country_code))


if __name__ == "__main__":
    app = ManualDedupApp()
    app.run()
