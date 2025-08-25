# Kissaten Frontend

A modern SvelteKit frontend for the Kissaten coffee bean discovery platform, built with shadcn-svelte components and Tailwind CSS.

## Features

- 🔍 **Unified Search**: Search across coffee beans, roasters, origins, and tasting notes
- 🏭 **Browse by Roaster**: Explore beans from specific roasters worldwide
- 🌍 **Browse by Country**: Discover beans by their country of origin
- 📱 **Responsive Design**: Mobile-friendly interface built with Tailwind CSS
- 🎨 **Modern UI**: Clean, accessible interface using shadcn-svelte components
- ⚡ **Fast Performance**: Built with SvelteKit for optimal performance

## Tech Stack

- **Framework**: SvelteKit
- **UI Components**: shadcn-svelte
- **Styling**: Tailwind CSS
- **Icons**: Lucide Svelte
- **Language**: TypeScript

## Getting Started

### Prerequisites

- Bun 1.0+ (recommended) or Node.js 18+

### Installation

1. Install dependencies:
```bash
bun install
```

2. Start the development server:
```bash
bun run dev
```

3. Open [http://localhost:5173](http://localhost:5173) in your browser

### Backend Connection

The frontend expects the Kissaten API to be running at `http://localhost:8000`. Make sure to start the FastAPI backend before using the frontend.

## Available Scripts

- `bun run dev` - Start development server
- `bun run build` - Build for production
- `bun run preview` - Preview production build
- `bun run check` - Run Svelte type checking
- `bun run lint` - Run ESLint
- `bun run format` - Format code with Prettier

## Project Structure

```
src/
├── routes/                 # SvelteKit routes
│   ├── +layout.svelte     # Main layout
│   ├── +page.svelte       # Home page
│   ├── search/            # Search page
│   ├── roasters/          # Roasters page
│   └── countries/         # Countries page
├── lib/
│   ├── components/ui/     # shadcn-svelte components
│   ├── api.ts            # API client
│   └── utils.ts          # Utility functions
├── app.css               # Global styles
└── app.html              # HTML template
```

## API Integration

The frontend integrates with the Kissaten FastAPI backend through a type-safe API client (`src/lib/api.ts`) that provides:

- Coffee bean search with filters
- Roaster information and bean listings
- Country-based filtering
- Pagination and sorting
- Statistics and analytics

## Responsive Design

The application is fully responsive with:
- Mobile-first design approach
- Collapsible filter sidebar on mobile
- Grid layouts that adapt to screen size
- Touch-friendly interface elements
- Accessible navigation

## Components

Key UI components include:
- **SearchFilters**: Advanced filtering interface
- **CoffeeBeanCard**: Individual bean display cards
- **RoasterCard**: Roaster information cards
- **CountryCard**: Country origin cards
- **Pagination**: Navigation for search results
