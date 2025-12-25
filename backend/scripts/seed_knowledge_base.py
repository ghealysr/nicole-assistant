#!/usr/bin/env python3
"""
Nicole V7 Knowledge Base Seeder

Populates the knowledge_base_files table from markdown files in the
knowledge/ directory.

Usage:
    cd backend
    python scripts/seed_knowledge_base.py

Or from project root:
    python -m backend.scripts.seed_knowledge_base
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import db
from app.services.knowledge_base_service import kb_service


# =============================================================================
# KNOWLEDGE FILES CONFIGURATION
# Maps markdown files to database entries with metadata
# =============================================================================

KNOWLEDGE_FILES = [
    # -------------------------------------------------------------------------
    # PATTERNS
    # -------------------------------------------------------------------------
    {
        "slug": "hero-sections",
        "title": "Hero Section Patterns & Conversion Optimization",
        "category": "patterns",
        "description": "Production hero patterns from Awwwards winners, conversion data, CTA psychology",
        "tags": ["hero", "conversion", "cta", "above-fold", "landing-pages", "design"],
        "path": "knowledge/patterns/hero-sections.md"
    },
    {
        "slug": "bento-grids",
        "title": "Bento Grid Design Systems",
        "category": "patterns",
        "description": "CSS Grid bento layouts, visual hierarchy, responsive patterns",
        "tags": ["bento-grid", "css-grid", "layout", "cards", "dashboard"],
        "path": "knowledge/patterns/bento-grids.md"
    },
    {
        "slug": "pricing-psychology",
        "title": "Pricing Page Psychology & Conversion",
        "category": "patterns",
        "description": "Pricing tier strategies, anchoring, decoy effect, A/B test data",
        "tags": ["pricing", "psychology", "conversion", "saas", "tiers"],
        "path": "knowledge/patterns/pricing-psychology.md"
    },
    
    # -------------------------------------------------------------------------
    # ANIMATION
    # -------------------------------------------------------------------------
    {
        "slug": "gsap-scrolltrigger",
        "title": "GSAP ScrollTrigger Advanced Production Techniques",
        "category": "animation",
        "description": "GSAP 3.14.2, ScrollTrigger patterns, React integration, performance optimization",
        "tags": ["gsap", "scrolltrigger", "animation", "react", "nextjs", "scroll"],
        "path": "knowledge/animation/gsap-scrolltrigger.md"
    },
    {
        "slug": "motion-react",
        "title": "Motion for React Production Guide",
        "category": "animation",
        "description": "Motion v12 (Framer Motion), bundle optimization, LazyMotion, React 19",
        "tags": ["framer-motion", "motion", "react", "animation", "nextjs", "gestures"],
        "path": "knowledge/animation/motion-react.md"
    },
    
    # -------------------------------------------------------------------------
    # COMPONENTS
    # -------------------------------------------------------------------------
    {
        "slug": "shadcn-reference",
        "title": "shadcn/ui Component Library Reference",
        "category": "components",
        "description": "Complete shadcn/ui reference: 56 components, forms, theming, accessibility",
        "tags": ["shadcn", "radix-ui", "react", "components", "tailwind", "forms"],
        "path": "knowledge/components/shadcn-reference.md"
    },
    {
        "slug": "aceternity-reference",
        "title": "Aceternity UI Component Library Reference",
        "category": "components",
        "description": "Animated components for landing pages, 90+ components, Framer Motion integration",
        "tags": ["aceternity", "animation", "landing-pages", "components", "framer-motion"],
        "path": "knowledge/components/aceternity-reference.md"
    },
    
    # -------------------------------------------------------------------------
    # FUNDAMENTALS (Design Systems)
    # -------------------------------------------------------------------------
    {
        "slug": "typography",
        "title": "Typography Systems & Type Scales",
        "category": "fundamentals",
        "description": "Type scales, fluid typography, font pairing, accessibility, variable fonts",
        "tags": ["typography", "fonts", "type-scale", "readability", "wcag", "clamp"],
        "path": "knowledge/fundamentals/typography.md"
    },
    {
        "slug": "color-theory",
        "title": "Color Theory & OKLCH Color Systems",
        "category": "fundamentals",
        "description": "OKLCH colors, color harmony, accessibility contrast, Tailwind v4",
        "tags": ["color", "oklch", "accessibility", "contrast", "tailwind", "theme"],
        "path": "knowledge/fundamentals/color-theory.md"
    },
    {
        "slug": "spacing-systems",
        "title": "Spacing Systems & Layout Rhythm",
        "category": "fundamentals",
        "description": "8pt grid, spacing scales, vertical rhythm, Tailwind spacing",
        "tags": ["spacing", "layout", "grid", "rhythm", "8pt", "tailwind"],
        "path": "knowledge/fundamentals/spacing-systems.md"
    },
    
    # -------------------------------------------------------------------------
    # CORE
    # -------------------------------------------------------------------------
    {
        "slug": "anti-patterns",
        "title": "Anti-Patterns & Common Mistakes",
        "category": "core",
        "description": "What NOT to do: accessibility failures, performance killers, UX mistakes",
        "tags": ["anti-patterns", "mistakes", "accessibility", "performance", "wcag", "ux"],
        "path": "knowledge/core/anti-patterns.md"
    },
    
    # -------------------------------------------------------------------------
    # QA - Quality Assurance Knowledge for QA Agents
    # -------------------------------------------------------------------------
    {
        "slug": "accessibility-wcag",
        "title": "Accessibility & WCAG 2.2 Compliance",
        "category": "qa",
        "description": "WCAG 2.2 AA requirements, color contrast, keyboard navigation, ARIA patterns, screen reader testing",
        "tags": ["accessibility", "wcag", "a11y", "aria", "screen-reader", "contrast", "keyboard"],
        "path": "knowledge/qa/accessibility-wcag.md"
    },
    {
        "slug": "react-typescript-patterns",
        "title": "React & TypeScript Code Review Patterns",
        "category": "qa",
        "description": "React best practices, TypeScript strict mode, hooks rules, component patterns, error handling",
        "tags": ["react", "typescript", "hooks", "patterns", "code-review", "best-practices"],
        "path": "knowledge/qa/react-typescript-patterns.md"
    },
    {
        "slug": "performance-web-vitals",
        "title": "Core Web Vitals & Performance Optimization",
        "category": "qa",
        "description": "LCP, INP, CLS optimization, bundle analysis, lazy loading, image optimization, caching strategies",
        "tags": ["performance", "web-vitals", "lcp", "cls", "inp", "lighthouse", "optimization"],
        "path": "knowledge/qa/performance-web-vitals.md"
    },
    {
        "slug": "css-tailwind-patterns",
        "title": "CSS & Tailwind Best Practices",
        "category": "qa",
        "description": "Tailwind v4 patterns, responsive design, dark mode, CSS specificity, z-index management",
        "tags": ["css", "tailwind", "responsive", "dark-mode", "specificity", "styles"],
        "path": "knowledge/qa/css-tailwind-patterns.md"
    },
]


async def seed_knowledge_base(force_update: bool = False):
    """
    Seed all knowledge base files from markdown.
    
    Args:
        force_update: If True, update existing files. Otherwise skip them.
    """
    # Connect to database
    await db.connect()
    
    # Get project root (parent of backend/)
    project_root = Path(__file__).parent.parent.parent
    
    print("\n🌱 Seeding Nicole V7 Knowledge Base")
    print("=" * 50)
    
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for file_config in KNOWLEDGE_FILES:
        file_path = project_root / file_config["path"]
        slug = file_config["slug"]
        
        # Check if file exists
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            error_count += 1
            continue
        
        # Read file content
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"❌ Error reading {slug}: {e}")
            error_count += 1
            continue
        
        # Check if already exists in database
        existing = await kb_service.get_file_by_slug(slug)
        
        if existing:
            if force_update:
                # Update existing file
                try:
                    result = await kb_service.update_file(
                        slug=slug,
                        content=content,
                        title=file_config["title"],
                        description=file_config["description"],
                        tags=file_config["tags"]
                    )
                    if result:
                        print(f"🔄 Updated: {slug} (v{result['version']}, {result['sections_count']} sections)")
                        updated_count += 1
                    else:
                        print(f"❌ Failed to update: {slug}")
                        error_count += 1
                except Exception as e:
                    print(f"❌ Error updating {slug}: {e}")
                    error_count += 1
            else:
                print(f"⏭️  Skipping: {slug} (already exists)")
                skipped_count += 1
            continue
        
        # Create new file
        try:
            result = await kb_service.create_file(
                slug=slug,
                title=file_config["title"],
                content=content,
                category=file_config["category"],
                description=file_config["description"],
                tags=file_config["tags"],
                created_by=1  # Glen's user_id
            )
            
            word_count = result.get('word_count', 0)
            sections = result.get('sections_count', 0)
            print(f"✅ Created: {slug} ({word_count:,} words, {sections} sections)")
            created_count += 1
            
        except Exception as e:
            print(f"❌ Error creating {slug}: {e}")
            error_count += 1
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Seeding Summary:")
    print(f"   ✅ Created: {created_count}")
    print(f"   🔄 Updated: {updated_count}")
    print(f"   ⏭️  Skipped: {skipped_count}")
    print(f"   ❌ Errors:  {error_count}")
    
    # Get stats
    stats = await kb_service.get_usage_stats()
    print(f"\n📚 Knowledge Base Stats:")
    print(f"   Total Files: {stats.get('total_files', 0)}")
    print(f"   Total Words: {stats.get('total_words', 0):,}")
    print(f"   Categories:  {stats.get('categories', 0)}")
    
    await db.disconnect()
    print("\n🎉 Knowledge base seeding complete!\n")


async def list_knowledge_base():
    """List all files in the knowledge base."""
    await db.connect()
    
    slugs = await kb_service.get_all_slugs()
    
    print(f"\n📚 Knowledge Base Files ({len(slugs)} total):")
    for slug in slugs:
        print(f"   • {slug}")
    
    await db.disconnect()


async def test_search(query: str):
    """Test search functionality."""
    await db.connect()
    
    print(f"\n🔍 Searching for: '{query}'")
    results = await kb_service.search_fulltext(query, limit=5)
    
    if results:
        print(f"\n📄 Found {len(results)} results:")
        for r in results:
            print(f"   • {r['title']} ({r['category']}) - relevance: {r['relevance']:.3f}")
    else:
        print("   No results found.")
    
    await db.disconnect()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Nicole V7 Knowledge Base Seeder")
    parser.add_argument("--force", "-f", action="store_true", 
                        help="Force update existing files")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List all knowledge base files")
    parser.add_argument("--search", "-s", type=str,
                        help="Test search with a query")
    
    args = parser.parse_args()
    
    if args.list:
        asyncio.run(list_knowledge_base())
    elif args.search:
        asyncio.run(test_search(args.search))
    else:
        asyncio.run(seed_knowledge_base(force_update=args.force))

