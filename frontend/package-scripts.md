# Frontend Development Scripts

## Quick Start

1. **Install dependencies**:
```bash
bun install
```

2. **Start development server**:
```bash
bun run dev
```

Visit http://localhost:5173

## Available Scripts

- `bun run dev` - Start development server with hot reload
- `bun run build` - Build for production
- `bun run preview` - Preview production build locally
- `bun run check` - Run Svelte type checking
- `bun run check:watch` - Run type checking in watch mode
- `bun run lint` - Run ESLint for code quality
- `bun run format` - Format code with Prettier
- `bun run test` - Run all tests
- `bun run test:unit` - Run unit tests with Vitest
- `bun run test:integration` - Run integration tests with Playwright

## Development Workflow

1. Make sure the backend is running at http://localhost:8000
2. Start the frontend dev server with `bun run dev`
3. Open http://localhost:5173 in your browser
4. Changes will automatically reload in the browser

## Building for Production

```bash
bun run build
bun run preview
```

The build output will be in the `build/` directory.
