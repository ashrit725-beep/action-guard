{
  "brand": {
    "name": "Vexen",
    "tagline": "Control AI.",
    "brand_attributes": [
      "serious",
      "modern",
      "technical",
      "trustworthy",
      "fast",
      "minimal",
      "enterprise-grade"
    ],
    "wordmark_treatment": {
      "concept": "Pure wordmark (no mascot). Tight tracking, slightly extended x-height feel. Optional subtle ‘X’ emphasis.",
      "implementation_notes": [
        "Set wordmark in heading font with tracking-tight and optical sizing.",
        "Use a single accent color only on the ‘x’ (optional) or a thin underline rule; never gradients.",
        "Keep logo area small and crisp in app shell (top-left)."
      ],
      "tailwind_example": "font-display tracking-tight text-[15px] sm:text-base text-foreground"
    }
  },

  "design_personality": {
    "north_star": "Make the ALLOW / APPROVAL_REQUIRED / BLOCK decision understandable in <30 seconds, and make auditability feel inevitable.",
    "style_fusion": {
      "layout_principle": "Swiss/International Typographic Style for dense console pages (grid, rhythm, left-aligned), fused with modern ‘bento’ blocks for landing + dashboard summaries.",
      "surface_style": "Crisp borders + subtle elevation (no heavy shadows). Dark mode default with high-contrast text and restrained accent.",
      "visual_centerpiece": "The product UI itself: decision trace stepper, audit log table, approvals queue. No robots, no neon sci-fi."
    }
  },

  "typography": {
    "google_fonts": {
      "display": {
        "family": "Space Grotesk",
        "weights": [400, 500, 600, 700],
        "usage": "Headings, navigation, metric labels"
      },
      "body": {
        "family": "IBM Plex Sans",
        "weights": [400, 500, 600],
        "usage": "Body copy, tables, forms"
      },
      "mono": {
        "family": "IBM Plex Mono",
        "weights": [400, 500, 600],
        "usage": "Agent IDs, permission slugs, code blocks, audit action chips"
      }
    },
    "tailwind_font_tokens": {
      "font-display": "'Space Grotesk', ui-sans-serif, system-ui",
      "font-sans": "'IBM Plex Sans', ui-sans-serif, system-ui",
      "font-mono": "'IBM Plex Mono', ui-monospace, SFMono-Regular"
    },
    "text_size_hierarchy": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl",
      "h2": "text-base md:text-lg",
      "body": "text-sm md:text-base",
      "small": "text-xs text-muted-foreground"
    },
    "table_typography": {
      "row": "text-sm",
      "meta": "text-xs text-muted-foreground",
      "mono_fields": "font-mono text-xs"
    }
  },

  "color_system": {
    "notes": [
      "Dark is default. Provide a theme toggle that switches the root class .dark.",
      "No purple. Use ocean-cyan + slate neutrals + amber for approvals.",
      "Statuses must be color-blind-safe: pair color + icon + label + shape.",
      "Gradients only as subtle section background accents (<20% viewport)."
    ],
    "semantic_tokens": {
      "decision": {
        "allow": "teal",
        "approval_required": "amber",
        "block": "rose"
      },
      "risk": {
        "low": "slate",
        "medium": "sky",
        "high": "amber",
        "critical": "rose"
      }
    },
    "css_variables": {
      "dark_default": {
        "--background": "222 47% 6%",
        "--foreground": "210 40% 98%",
        "--card": "222 47% 8%",
        "--card-foreground": "210 40% 98%",
        "--popover": "222 47% 8%",
        "--popover-foreground": "210 40% 98%",
        "--primary": "190 95% 42%",
        "--primary-foreground": "222 47% 6%",
        "--secondary": "222 28% 14%",
        "--secondary-foreground": "210 40% 98%",
        "--muted": "222 28% 14%",
        "--muted-foreground": "215 20% 70%",
        "--accent": "222 28% 14%",
        "--accent-foreground": "210 40% 98%",
        "--destructive": "355 78% 56%",
        "--destructive-foreground": "210 40% 98%",
        "--border": "222 22% 18%",
        "--input": "222 22% 18%",
        "--ring": "190 95% 42%",

        "--vexen-surface-2": "222 30% 10%",
        "--vexen-surface-3": "222 26% 12%",
        "--vexen-gridline": "222 18% 22%",

        "--status-allow": "173 80% 40%",
        "--status-allow-bg": "173 80% 40% / 0.14",
        "--status-approval": "38 92% 50%",
        "--status-approval-bg": "38 92% 50% / 0.14",
        "--status-block": "355 78% 56%",
        "--status-block-bg": "355 78% 56% / 0.14",

        "--risk-low": "215 16% 70%",
        "--risk-medium": "199 89% 60%",
        "--risk-high": "38 92% 50%",
        "--risk-critical": "355 78% 56%"
      },
      "light": {
        "--background": "210 40% 99%",
        "--foreground": "222 47% 11%",
        "--card": "0 0% 100%",
        "--card-foreground": "222 47% 11%",
        "--popover": "0 0% 100%",
        "--popover-foreground": "222 47% 11%",
        "--primary": "190 95% 34%",
        "--primary-foreground": "210 40% 99%",
        "--secondary": "210 30% 96%",
        "--secondary-foreground": "222 47% 11%",
        "--muted": "210 30% 96%",
        "--muted-foreground": "215 16% 40%",
        "--accent": "210 30% 96%",
        "--accent-foreground": "222 47% 11%",
        "--destructive": "355 78% 46%",
        "--destructive-foreground": "210 40% 99%",
        "--border": "214 20% 90%",
        "--input": "214 20% 90%",
        "--ring": "190 95% 34%",

        "--vexen-surface-2": "210 30% 97%",
        "--vexen-surface-3": "210 30% 95%",
        "--vexen-gridline": "214 20% 88%",

        "--status-allow": "173 80% 30%",
        "--status-allow-bg": "173 80% 30% / 0.10",
        "--status-approval": "38 92% 42%",
        "--status-approval-bg": "38 92% 42% / 0.10",
        "--status-block": "355 78% 46%",
        "--status-block-bg": "355 78% 46% / 0.10",

        "--risk-low": "215 16% 40%",
        "--risk-medium": "199 89% 40%",
        "--risk-high": "38 92% 42%",
        "--risk-critical": "355 78% 46%"
      }
    },
    "allowed_gradients": {
      "usage": [
        "Landing hero background only (decorative overlay)",
        "Very subtle section separators"
      ],
      "examples": [
        "radial-gradient(900px circle at 20% 10%, hsla(190,95%,42%,0.18), transparent 55%)",
        "radial-gradient(700px circle at 80% 0%, hsla(38,92%,50%,0.10), transparent 60%)"
      ],
      "restriction": "Never exceed 20% viewport coverage; never behind dense tables or long-form text."
    }
  },

  "tokens": {
    "spacing": {
      "page_padding": "px-4 sm:px-6 lg:px-8",
      "section_padding": "py-14 sm:py-18",
      "stack": {
        "xs": "gap-2",
        "sm": "gap-3",
        "md": "gap-4",
        "lg": "gap-6",
        "xl": "gap-8"
      }
    },
    "radius": {
      "sm": "rounded-md",
      "md": "rounded-lg",
      "lg": "rounded-xl"
    },
    "borders": {
      "default": "border border-border",
      "hairline": "border border-border/70"
    },
    "shadows": {
      "card": "shadow-[0_1px_0_hsla(0,0%,100%,0.04),0_12px_30px_hsla(222,47%,2%,0.35)] dark:shadow-[0_1px_0_hsla(0,0%,100%,0.04),0_18px_40px_hsla(222,47%,2%,0.55)]",
      "popover": "shadow-[0_18px_50px_hsla(222,47%,2%,0.45)]"
    }
  },

  "layout": {
    "grid": {
      "landing": "max-w-6xl mx-auto",
      "app_shell": {
        "sidebar_width": "w-[280px]",
        "content_max": "max-w-[1400px]",
        "content_padding": "px-4 sm:px-6 lg:px-8 py-6"
      }
    },
    "navigation": {
      "pattern": "Protected app uses persistent sidebar + topbar. Public pages use minimal top nav.",
      "sidebar_sections": [
        "Overview",
        "Agents",
        "Approvals",
        "Audit Log",
        "Security Center",
        "Policies",
        "Simulator",
        "Developers",
        "Settings"
      ]
    }
  },

  "components": {
    "component_path": {
      "button": "/app/frontend/src/components/ui/button.jsx",
      "badge": "/app/frontend/src/components/ui/badge.jsx",
      "card": "/app/frontend/src/components/ui/card.jsx",
      "table": "/app/frontend/src/components/ui/table.jsx",
      "tabs": "/app/frontend/src/components/ui/tabs.jsx",
      "dialog": "/app/frontend/src/components/ui/dialog.jsx",
      "sheet": "/app/frontend/src/components/ui/sheet.jsx",
      "dropdown_menu": "/app/frontend/src/components/ui/dropdown-menu.jsx",
      "select": "/app/frontend/src/components/ui/select.jsx",
      "input": "/app/frontend/src/components/ui/input.jsx",
      "textarea": "/app/frontend/src/components/ui/textarea.jsx",
      "switch": "/app/frontend/src/components/ui/switch.jsx",
      "tooltip": "/app/frontend/src/components/ui/tooltip.jsx",
      "scroll_area": "/app/frontend/src/components/ui/scroll-area.jsx",
      "separator": "/app/frontend/src/components/ui/separator.jsx",
      "sonner_toast": "/app/frontend/src/components/ui/sonner.jsx",
      "calendar": "/app/frontend/src/components/ui/calendar.jsx",
      "skeleton": "/app/frontend/src/components/ui/skeleton.jsx"
    },

    "status_badges": {
      "decisions": {
        "ALLOW": {
          "label": "Allowed",
          "icon": "CheckCircle",
          "classes": "bg-[hsl(var(--status-allow-bg))] text-[hsl(var(--status-allow))] border border-[hsl(var(--status-allow)/0.35)]",
          "data_testid": "decision-badge-allow"
        },
        "APPROVAL_REQUIRED": {
          "label": "Approval required",
          "icon": "ShieldAlert",
          "classes": "bg-[hsl(var(--status-approval-bg))] text-[hsl(var(--status-approval))] border border-[hsl(var(--status-approval)/0.35)]",
          "data_testid": "decision-badge-approval-required"
        },
        "BLOCK": {
          "label": "Blocked",
          "icon": "XCircle",
          "classes": "bg-[hsl(var(--status-block-bg))] text-[hsl(var(--status-block))] border border-[hsl(var(--status-block)/0.35)]",
          "data_testid": "decision-badge-block"
        }
      },
      "risk": {
        "LOW": {
          "icon": "SignalLow",
          "classes": "bg-muted text-foreground/80 border border-border",
          "data_testid": "risk-badge-low"
        },
        "MEDIUM": {
          "icon": "SignalMedium",
          "classes": "bg-[hsl(199_89%_60%/0.12)] text-[hsl(199_89%_60%)] border border-[hsl(199_89%_60%/0.35)]",
          "data_testid": "risk-badge-medium"
        },
        "HIGH": {
          "icon": "SignalHigh",
          "classes": "bg-[hsl(var(--status-approval-bg))] text-[hsl(var(--status-approval))] border border-[hsl(var(--status-approval)/0.35)]",
          "data_testid": "risk-badge-high"
        },
        "CRITICAL": {
          "icon": "Siren",
          "classes": "bg-[hsl(var(--status-block-bg))] text-[hsl(var(--status-block))] border border-[hsl(var(--status-block)/0.35)]",
          "data_testid": "risk-badge-critical"
        }
      },
      "badge_shape": "Use shadcn Badge with icon + label; never color-only."
    },

    "metric_cards": {
      "pattern": "4-up responsive cards with label, value, delta, and tiny sparkline placeholder (optional).",
      "classes": "rounded-xl border border-border bg-card p-4 sm:p-5",
      "data_testid": "dashboard-metric-card"
    },

    "tables": {
      "audit_log": {
        "requirements": [
          "Sticky header",
          "Row hover highlight",
          "Monospace chips for action/resource",
          "Decision badge column",
          "Expandable row details via Sheet/Drawer (do not navigate away)"
        ],
        "sticky_header_classes": "sticky top-0 z-10 bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/70",
        "row_classes": "hover:bg-muted/40",
        "data_testid": {
          "table": "audit-log-table",
          "search": "audit-log-search-input",
          "filter": "audit-log-filter-chip",
          "row": "audit-log-row"
        }
      },
      "agents_list": {
        "requirements": [
          "Dense but breathable",
          "Pinned first column (Agent)",
          "Status + Risk badges",
          "Permission count as link",
          "Kebab menu actions"
        ],
        "data_testid": {
          "table": "agents-table",
          "create": "agents-create-button",
          "template_library": "agent-template-library"
        }
      }
    },

    "decision_trace_stepper": {
      "signature_moment": true,
      "visual": "13-step vertical stepper with per-step state: PASS / ESCALATE / FAIL. Each step shows check name, short reason, and latency.",
      "implementation": {
        "container": "rounded-xl border border-border bg-card",
        "step_row": "flex items-start gap-3 px-4 py-3",
        "left_rail": "w-6 flex flex-col items-center",
        "dot": {
          "pass": "h-2.5 w-2.5 rounded-full bg-[hsl(var(--status-allow))]",
          "escalate": "h-2.5 w-2.5 rounded-full bg-[hsl(var(--status-approval))]",
          "fail": "h-2.5 w-2.5 rounded-full bg-[hsl(var(--status-block))]"
        },
        "connector": "w-px flex-1 bg-border",
        "title": "font-display text-sm",
        "reason": "text-xs text-muted-foreground",
        "meta": "font-mono text-[11px] text-muted-foreground"
      },
      "data_testid": {
        "panel": "decision-trace-panel",
        "step": "decision-trace-step"
      }
    },

    "approvals_queue": {
      "card": {
        "layout": "Left: agent + action + resource. Right: amount + risk + requested time. Bottom: reason + Approve/Deny.",
        "actions": "Approve (primary) + Deny (destructive outline).",
        "data_testid": {
          "list": "approvals-queue-list",
          "approve": "approval-approve-button",
          "deny": "approval-deny-button"
        }
      }
    },

    "template_cards": {
      "grid": "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4",
      "card": "rounded-xl border border-border bg-card p-4 hover:bg-muted/30",
      "micro": "On hover: show ‘Deploy’ button and permission count; keep motion subtle.",
      "data_testid": {
        "search": "template-library-search-input",
        "category": "template-library-category-filter",
        "deploy": "template-library-deploy-button"
      }
    },

    "code_blocks": {
      "use_case": "Developer API docs and policy JSON previews.",
      "classes": "rounded-xl border border-border bg-[hsl(var(--vexen-surface-2))] p-4 font-mono text-xs overflow-auto",
      "data_testid": "code-block"
    }
  },

  "pages": {
    "landing_page": {
      "structure": [
        {
          "section": "Top Nav",
          "content": "Vexen wordmark left; right: Docs (Developers), Pricing (optional placeholder), Sign in, Create an Agent.",
          "notes": "Keep nav minimal; use shadcn NavigationMenu or simple flex row."
        },
        {
          "section": "Hero",
          "headline": "Give AI agents power. Keep control.",
          "supporting": "Vexen sits between your agents and the systems they touch—identity, permissions, limits, approvals, monitoring, audit history.",
          "cta": [
            "Create an Agent (primary)",
            "Watch Demo (secondary)"
          ],
          "visual": "Inline product diagram: Agent → Vexen → Real-World Action, plus a compact 5-node pipeline: Identity → Permissions → Policy → Decision → Audit.",
          "layout": "Two-column on desktop; stacked on mobile. Visual is a card with subtle gridlines and animated decision pulses.",
          "data_testid": {
            "primary_cta": "landing-create-agent-button",
            "secondary_cta": "landing-watch-demo-button"
          }
        },
        {
          "section": "How it works (30s)",
          "content": "3-step strip: 1) Agent requests action 2) Vexen evaluates 13 checks 3) Decision + audit event.",
          "component": "Cards with icons + short copy."
        },
        {
          "section": "Capabilities",
          "content": "Bento grid: Agent Identity, Granular Permissions, Spending Limits, Temporary Access, Human Approval, Activity Monitoring, Audit Logs.",
          "notes": "Each tile includes a tiny UI snippet (badge/table row) rather than illustrations."
        },
        {
          "section": "Signature moment preview",
          "content": "A static-but-realistic screenshot-like panel of the 13-step trace with one step escalating to approval.",
          "notes": "Use actual components; keep it lightweight."
        },
        {
          "section": "Trust / Compliance",
          "content": "Short list: Default deny, deny-wins, immutable audit trail, least privilege templates.",
          "notes": "No fake logos."
        },
        {
          "section": "Footer",
          "content": "Links: Security, Developers, Contact, Terms, Privacy."
        }
      ]
    },

    "contact_page": {
      "layout": "Split layout: left founder card stack + right contact form.",
      "founders": [
        {
          "name": "Ashrit Talluri",
          "role": "Co-founder",
          "image_url": "https://images.unsplash.com/photo-1573497619860-6d82917e4ec8?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjh8MHwxfHNlYXJjaHw0fHxjbGVhbiUyMGVudGVycHJpc2UlMjB0ZWFtJTIwcG9ydHJhaXQlMjBmb3VuZGVycyUyMG9mZmljZXxlbnwwfHx8Ymx1ZXwxNzg3OTY5NTEzfDA&ixlib=rb-4.1.0&q=85"
        },
        {
          "name": "Aditya Mirchandani",
          "role": "Co-founder",
          "image_url": "https://images.unsplash.com/photo-1526560244950-1a3c1ace48f9?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjh8MHwxfHNlYXJjaHwxfHxjbGVhbiUyMGVudGVycHJpc2UlMjB0ZWFtJTIwcG9ydHJhaXQlMjBmb3VuZGVycyUyMG9mZmljZXxlbnwwfHx8Ymx1ZXwxNzg3OTY5NTEzfDA&ixlib=rb-4.1.0&q=85"
        }
      ],
      "form_fields": ["Name", "Work email", "Company", "Message"],
      "data_testid": {
        "form": "contact-form",
        "submit": "contact-form-submit-button"
      }
    },

    "simulator": {
      "visual_choreography": [
        "Left column: scripted action timeline (step 1..n) with live status badges.",
        "Right column: Decision panel showing decision badge + reason + 13-step trace.",
        "Inline approval moment: when APPROVAL_REQUIRED occurs, open a Sheet from right with Approve/Deny; decision updates timeline row in-place.",
        "End summary card: 2 Allowed / 1 Approval Required / 1 Blocked / $0 unauthorized spending."
      ],
      "labels": "Every simulated element must be clearly marked SIMULATED with a small badge in the header.",
      "data_testid": {
        "run": "simulator-run-button",
        "timeline": "simulator-timeline",
        "summary": "simulator-summary"
      }
    }
  },

  "motion": {
    "principles": [
      "Motion must clarify state changes (decision outcomes, approvals) rather than decorate.",
      "Prefer cheap CSS transitions; avoid heavy animation libs unless necessary.",
      "Respect prefers-reduced-motion."
    ],
    "micro_interactions": {
      "buttons": "transition-colors duration-150; active: scale-[0.98] (only on press).",
      "cards": "hover:bg-muted/30 with subtle border emphasis; no floating animations.",
      "table_rows": "hover highlight + left accent bar for decision state.",
      "simulator": "New timeline row fades in (opacity) and slides 4px (translate-y) only."
    }
  },

  "accessibility": {
    "requirements": [
      "WCAG AA contrast in both themes.",
      "Visible focus rings using --ring.",
      "Do not rely on color alone for decision/risk; always include icon + label.",
      "Keyboard navigable dialogs/sheets/tables.",
      "Use aria-labels for icon-only buttons."
    ],
    "focus_styles": "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
  },

  "performance": {
    "guidance": [
      "Tables: use virtualization if needed later; for now ensure sticky headers and avoid heavy shadows per row.",
      "Avoid large images; use subtle CSS noise instead of big textures.",
      "Keep gradients minimal and only in hero backgrounds."
    ]
  },

  "image_urls": {
    "decorative_backgrounds": [
      {
        "category": "landing-hero-subtle-texture",
        "description": "Optional subtle abstract texture behind hero (use with low opacity overlay).",
        "url": "https://images.unsplash.com/photo-1650488908294-07186d808e5d?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2ODh8MHwxfHNlYXJjaHwxfHxtaW5pbWFsJTIwYWJzdHJhY3QlMjBncmFpbiUyMHRleHR1cmUlMjBkYXJrJTIwYmFja2dyb3VuZHxlbnwwfHx8dGVhbHwxNzg3OTY5NTA4fDA&ixlib=rb-4.1.0&q=85"
      }
    ],
    "contact_founders": [
      {
        "category": "founder-portrait-placeholder",
        "description": "Use as placeholder portrait cards (do not imply these are the founders).",
        "url": "https://images.unsplash.com/photo-1573497619860-6d82917e4ec8?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjh8MHwxfHNlYXJjaHw0fHxjbGVhbiUyMGVudGVycHJpc2UlMjB0ZWFtJTIwcG9ydHJhaXQlMjBmb3VuZGVycyUyMG9mZmljZXxlbnwwfHx8Ymx1ZXwxNzg3OTY5NTEzfDA&ixlib=rb-4.1.0&q=85"
      },
      {
        "category": "founder-portrait-placeholder",
        "description": "Second placeholder portrait option.",
        "url": "https://images.unsplash.com/photo-1526560244950-1a3c1ace48f9?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjh8MHwxfHNlYXJjaHwxfHxjbGVhbiUyMGVudGVycHJpc2UlMjB0ZWFtJTIwcG9ydHJhaXQlMjBmb3VuZGVycyUyMG9mZmljZXxlbnwwfHx8Ymx1ZXwxNzg3OTY5NTEzfDA&ixlib=rb-4.1.0&q=85"
      }
    ]
  },

  "libraries": {
    "recommended": [
      {
        "name": "lucide-react",
        "why": "Consistent iconography for decisions/risk and navigation.",
        "usage": "Use icons: CheckCircle, XCircle, ShieldAlert, Siren, SignalLow/Medium/High, KeyRound, FileKey, Activity, Shield, ScrollText."
      }
    ],
    "avoid": [
      "Heavy WebGL backgrounds",
      "Particle libraries",
      "Large Lottie animations"
    ]
  },

  "data_testid_policy": {
    "rule": "All interactive and key informational elements MUST include data-testid in kebab-case.",
    "examples": [
      "data-testid=\"theme-toggle\"",
      "data-testid=\"sidebar-nav-agents\"",
      "data-testid=\"agents-create-button\"",
      "data-testid=\"audit-log-search-input\"",
      "data-testid=\"approval-approve-button\"",
      "data-testid=\"policy-generator-submit-button\""
    ]
  },

  "instructions_to_main_agent": [
    "Update /app/frontend/src/index.css tokens to match the provided dark_default + light palettes; keep shadcn variable structure.",
    "Remove CRA starter styles from /app/frontend/src/App.css (centered header/logo spin). Do not center the app container.",
    "Implement theme toggle by toggling .dark on <html> or <body>; default to dark.",
    "Create reusable status badge component (DecisionBadge, RiskBadge) using shadcn Badge + lucide icons; never color-only.",
    "Audit Log: implement sticky header, filter chips, search input, and row detail Sheet. Ensure all controls have data-testid.",
    "Simulator: implement two-column layout with timeline + decision panel; inline approval via Sheet; end summary card with 2/1/1/$0.",
    "Use only existing shadcn components from /src/components/ui (Button, Badge, Card, Table, Tabs, Dialog, Sheet, Select, DropdownMenu, ScrollArea, Skeleton, Sonner).",
    "All new components must be .js (not .tsx) and follow named export convention; pages default export.",
    "Ensure dense pages use max-w-[1400px] and strong spacing; avoid cluttered charts."
  ],

  "GENERAL_UI_UX_DESIGN_GUIDELINES": "    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals."
}
