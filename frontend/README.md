# LeadOps Agent Frontend

Next.js 14 frontend for the LeadOps Agent B2B agentic workflow system.

## Features

- Dashboard with KPI cards and leads table
- CSV upload with drag & drop
- Lead detail pages with scoring, email drafts, and activity timeline
- Settings page for configuring scoring weights and thresholds
- Real-time processing stream via SSE
- Professional B2B SaaS UI with Tailwind CSS
- Dark mode support

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running on `http://localhost:8000`

### Installation

```bash
npm install
```

### Configuration

Create a `.env.local` file:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js 14 App Router pages
│   │   ├── layout.tsx         # Root layout with sidebar
│   │   ├── page.tsx           # Dashboard
│   │   ├── leads/[id]/        # Lead detail page
│   │   ├── upload/            # CSV upload page
│   │   └── settings/          # Settings page
│   ├── components/            # React components
│   │   ├── dashboard/         # KPI cards
│   │   ├── leads/             # Lead table, score badge, timeline, feedback
│   │   ├── email/             # Email editor
│   │   └── upload/            # CSV upload form
│   ├── lib/                   # Core utilities
│   │   ├── api.ts            # API client functions
│   │   └── types.ts          # TypeScript types
│   └── hooks/                 # Custom React hooks
│       └── use-processing-stream.ts  # SSE hook
├── public/                    # Static assets
├── package.json
├── tsconfig.json
├── next.config.ts
└── tailwind.config.ts
```

## API Integration

The frontend connects to the FastAPI backend via the API client in `/src/lib/api.ts`. All API endpoints are typed with TypeScript interfaces defined in `/src/lib/types.ts`.

## Styling

- Tailwind CSS for utility-first styling
- Custom CSS variables for theming in `globals.css`
- Lucide React for icons
- Professional B2B SaaS aesthetic with slate-based color palette
