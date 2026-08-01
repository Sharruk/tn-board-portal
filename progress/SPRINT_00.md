# Sprint 00: Architecture Planning (Version 2)

## Project Vision
TN Board Portal aims to provide a single, free, publicly accessible platform for Tamil Nadu State Board students to find official question papers, answer keys, official notices, and news. Version 2 expands on the robust Version 1 foundation to scale the application with a dedicated backend service, enabling more complex business logic, better search capabilities, and future platform expansion (e.g., community Q&A, student accounts).

## Current Architecture (React + Supabase)
- **Frontend**: React 18 SPA built with Vite and Tailwind CSS, hosted on Vercel.
- **Backend/BaaS**: Supabase handles Postgres database, Auth, and Storage.
- **Data Flow**: The React frontend communicates directly with Supabase via the JS client. Complex operations are handled via PostgreSQL RPC functions.
- **Security**: Row Level Security (RLS) is strictly enforced at the database level.

## Future Architecture (React + FastAPI + Supabase)
- **Frontend**: React SPA (remains on Vercel).
- **Backend**: FastAPI (Python) service to handle complex business logic, API rate limiting, search enhancements, and background tasks.
- **Database/Auth/Storage**: Supabase remains the primary data layer. The FastAPI backend will interact with Supabase (via server-side client/SQL) and expose REST endpoints to the frontend.
- **Data Flow**: Frontend -> FastAPI -> Supabase. (Some direct Supabase calls may remain for simple queries or real-time features if appropriate, but complex business logic moves to FastAPI).

## Reasons for Migration
- **Complex Business Logic**: PostgreSQL RPCs are powerful but harder to maintain and test as business logic grows (e.g., advanced search, email notifications, OCR pipelines).
- **Rate Limiting & Security**: A dedicated backend allows for granular rate limiting, request validation, and better protection against abuse.
- **Third-Party Integrations**: FastAPI makes it easier to integrate with external APIs and AI tools for future features.
- **Scalability**: Decoupling the business logic from the database layer prepares the architecture for larger scale and additional client apps (e.g., mobile).

## Expected Benefits
- Improved developer experience and testability for business logic.
- Better performance and caching mechanisms via the backend layer.
- Enhanced search quality and flexibility.
- Preparation for advanced features (AI suggestions, automated OCR).

## Major Milestones
1. **M1: Architecture Planning & Setup** (Current Sprint)
2. **M2: FastAPI Foundation** (Setup FastAPI, routing, Supabase server client)
3. **M3: API Parity** (Replicate current RPCs and direct queries as FastAPI endpoints)
4. **M4: Frontend Integration** (Update frontend services to point to FastAPI)
5. **M5: Deployment & CI/CD** (Deploy FastAPI backend and update pipelines)
6. **M6: Feature Enhancements** (Implement tsvector search, rate limiting, etc.)

## Estimated Sprint Breakdown
- **Sprint 00**: Architecture Planning (Documentation only) - *We are here*
- **Sprint 01**: FastAPI Foundation & Basic Endpoints (M2)
- **Sprint 02**: Achieve API Parity & Frontend Integration (M3, M4)
- **Sprint 03**: Deployment Setup & Production Rollout (M5)
- **Sprint 04**: Implement v1.1 Features (Search Upgrade, SEO, Rate Limiting) (M6)
