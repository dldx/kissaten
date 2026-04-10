# Guided Coffee Tasting Implementation Plan

## Overview
The Guided Coffee Tasting feature provides a conversational, wizard-like interface for users to evaluate and record the sensory profile of coffee. It uses the SCA (Specialty Coffee Association) flavor lexicon and common tasting descriptors to build a structured flavor profile that can be saved locally and used for searching matching beans.

## Architecture

### 1. Data Layer (`frontend/src/lib/tasting/conversation.ts`)
- **Flavor Taxonomy**: Hierarchical structure of flavor categories (Fruits, Floral, Sweet, etc.).
- **Guided Questions**: Category-specific prompts to help users identify specific notes.
- **Defect Mapping**: Inclusion of "off-flavors" (phenolic, rubbery, etc.) mapped to SCA standards.
- **Sensory Basics**: Intensity scales for Acidity, Sweetness, and Bitterness.
- **Physical Attributes**: Mouthfeel and Body descriptions.

### 2. Persistence (`frontend/src/lib/db/localdb.ts`)
- **IndexedDB via Dexie.js**: Client-side storage for tasting sessions.
- **Schema Management**:
  - `Version 1-2`: Initial setup for collections.
  - `Version 3`: Added `name` index and interface field for session labeling.
- **Data Integrity**: Uses `$state.snapshot` to strip Svelte reactive proxies before serialization to IndexedDB.

### 3. UI/UX Design (`frontend/src/lib/components/tasting/`)
- **TastingWizard.svelte**: Core state machine managing steps (`basics` -> `overview` -> `category` -> `mouthfeel` -> `summary`).
- **CategoryTile.svelte**: Visual selection buttons for broad flavor families.
- **FlavorChip.svelte**: Interactive toggles for specific tasting notes.
- **WizardProgress.svelte**: Visual indicator of the user's journey through the appraisal.

## Implementation Details

### State Management
- Built with **Svelte 5 Runes** (`$state`, `$derived`).
- Comprehensive state tracking for:
  - Selected categories and specific notes.
  - Mouthfeel and sensory base intensities.
  - Custom session naming.

### Features
- **Conversational UI**: Sequential questions reduce cognitive load compared to a single large form.
- **Session History**: Dedicated view (`/tasting/history`) to review platform-local sessions.
- **Search Integration**: Functionality to convert tasting results into a search query for the Kissaten bean database.
- **Feedback System**: `svelte-sonner` integration for success/error notifications during save operations.

## Design Notes
- **Color Coding**: Category-specific colors (e.g., Red for Berry, Yellow for Citrus) provide visual cues.
- **Accessibility**: ARIA-compliant naming and keyboard-navigable buttons.
- **Responsive Layout**: Mobile-first grid systems for flavor selection tiles.
- **Error Prevention**: Manual save trigger on the summary screen to prevent redundant database entries and ensure custom names are captured.
