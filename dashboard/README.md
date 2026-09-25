# IGWT-PF26 Dashboard

iPhone-responsive quant research dashboard for Layer 1-7 visualization and real-time signal monitoring.

## Structure

```
dashboard/
├── app/
│   ├── layout.tsx          # Root layout + nav
│   ├── page.tsx            # Main dashboard
│   ├── globals.css         # Global styles
│   └── signals/            # (Future) Detailed signals view
│       └── page.tsx
├── components/
│   ├── RegimeCard.tsx      # Market regime detection
│   ├── BCECard.tsx         # Bottom confirmation engine
│   ├── X20Card.tsx         # Opportunity detection
│   ├── NARMCard.tsx        # Narrative rotation
│   ├── RCMCard.tsx         # Rotation confirmation
│   ├── RRPCard.tsx         # Revival radar
│   └── AlertPanel.tsx      # Active signals
├── package.json
├── next.config.js
├── tsconfig.json
├── tailwind.config.ts
└── postcss.config.js
```

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **UI**: React 18 + Tailwind CSS
- **Charts**: Recharts (ready for integration)
- **Type Safety**: TypeScript strict mode
- **Mobile First**: iPhone-responsive design

## Features

- **Real-time monitoring**: All 7 layers visualized
- **Mobile-first**: Optimized for iPhone, scales to desktop
- **Dark mode**: Professional dark theme for quant analysis
- **Responsive layout**: Auto-adapts to device size
- **Component-based**: Modular card structure

## Layer Mapping

| Layer | Component | Purpose |
|-------|-----------|---------|
| 2 | RegimeCard | Market regime detection |
| 3 | BCECard | Bottom confirmation scoring |
| 4 | X20Card | Asymmetric opportunity |
| 5 | NARMCard | Narrative rotation |
| 6 | RCMCard | Rotation confirmation |
| 7 | RRPCard | Revival radar |
| Alert | AlertPanel | Active signals |

## Setup

```bash
cd dashboard
npm install
npm run dev
```

Open http://localhost:3000

## Build

```bash
npm run build
npm start
```

## Type Check

```bash
npm run type-check
```

## Production Deployment

- Vercel (recommended)
- Docker: Build `./dashboard` as standalone
- Environment: Node 18+

## Future Enhancements

- Backend API integration (FastAPI)
- WebSocket for real-time updates
- Historical charts & analytics
- Portfolio tracking
- Custom alerts
- Mobile app (React Native)
