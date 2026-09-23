# Analytics interface review

## Scope and coverage

Reviewed the authenticated shell and `/analytics/` dashboard after the V6 visual redesign. The stack is Django templates, plain JavaScript, and CSS custom properties. Product conventions came from `PROJECT.md`, `README-WEB.md`, and `docs/V6-ANALYTICS.md`; no project-local interface style guide was found. Other screens and the separate `milenio/ui` interface are outside scope.

| Domain | Evidence inspected | Result |
| --- | --- | --- |
| Accessibility | `base.html`, `dashboard.html`, `shell.js`, `analytics.js`, focus rules, chart/table semantics; reported keyboard interactions | No actionable finding in the reviewed flow; screen reader unverified |
| Layout | Shell, KPI, chart, tables, breakpoints; reported 320px and 574px reflow inspections | No actionable finding at tested widths; native 200% zoom unverified |
| Writing | Actions, filter error, no-result and empty states | No actionable finding in inspected states |
| Typography | Declared sizes, wrapping, currency values at desktop and 320px | No actionable finding in inspected values |
| Colors | Declared foreground/background pairs measured with WCAG relative luminance; chart series treatment | No measured failure in reviewed pairs; rendered focus and grayscale checks unverified |
| UI | Button hierarchy, tab, chart, search and sort states | No actionable finding in inspected states |

## Findings

No actionable interface findings remain in the reviewed scope.

The source baseline issues were addressed during implementation:

| Location | Before | After | Why |
| --- | --- | --- | --- |
| `workshop/static/workshop/app.css:3`; `workshop/static/workshop/shell.css:31` | Mobile navigation could scroll horizontally without a visible cue. | A labeled menu toggle exposes all links; Escape closes it and restores focus. | Every destination is discoverable and keyboard reachable. |
| `workshop/static/workshop/analytics.css:6`; `workshop/templates/workshop/dashboard.html:16` | Chart series differed only by color. | Payment series and its legend/readout use a dashed pattern; exact values remain in a table. | Series identity does not depend on color alone. |
| `workshop/static/workshop/analytics.css:20` | KPI currency values could truncate. | Full values wrap and fit the tested desktop and mobile cards. | Monetary amounts remain available without overlap. |
| `workshop/static/workshop/analytics.css:1`; `workshop/static/workshop/shell.css:6` | Several small-text colors failed the declared-pair 4.5:1 check. | Reviewed colors were darkened; `#627086` measures 5.02:1 on white and 4.72:1 on `#f6f8fa`. | Small text reaches the applicable contrast threshold on those surfaces. |
| `workshop/templates/workshop/dashboard.html:7`; `workshop/templates/workshop/analytics/filters.html:1` | A filter error replaced the form. | The form stays present with valid submitted values and a Spanish recovery message. | Readers can correct date order or range without rebuilding all filters. |
| `workshop/templates/workshop/dashboard.html:17`, `workshop/templates/workshop/dashboard.html:19`; `workshop/templates/workshop/analytics/filters.html:1` | Empty states lacked a next step; “Aplicar” competed with “Actualizar y revisar” as a filled primary button. | Empty states link to filters; “Aplicar” is secondary. | The interface gives a recovery path and clearer action hierarchy. |

## Verification

**Source checks completed:** Read the template, CSS, JavaScript, presentation helper, and dashboard view. Confirmed that table search scans visible name/type or name/SKU cells; the selected-versus-latest comparison prevents a quick range from falsely marking the latest cut as historical.

**Rendered checks reported by the implementation reviewer:** At 1147px, chart End selected 22 September and showed invoiced 1,102 and payments 300 matching the day's data. Service/part search, no-result state, clearing, and ascending cost sort worked; the observed sort values were 200, 285, 340, 1,020, 1,400. The Follow-up section showed 41 pending proposals, one open action, one closed action, and six mart links. Tabs and the “Ver detalle” jump maintained scroll position, updated the active state, and supported keyboard focus. At 320px, document scroll width was 305px and the demand tables scrolled within their own containers; all four KPI amounts remained fully visible, including $15,265.60 and $12,033.40. The mobile menu opened with focus on the brand; Escape returned focus to the toggle. At 574px, document scroll width was 559px.

A reversed 22 September–1 September filter returned a Spanish correction message while retaining both dates, the fleet segment, and cut 7. An empty 1–7 January 2000 period showed zero cards without a fabricated percentage, a flat chart, and an “Ajustar filtros” link. Selecting cut 1 displayed “Histórico”; latest cut 7 did not. No JavaScript console errors appeared in these checked flows.

**Not verified:** This reviewer did not independently operate the browser or a screen reader. The in-app browser zoom commands did not change the viewport, so native 200% zoom remains unverified. Rendered focus-ring contrast, grayscale chart appearance, and first-cut and stale-cut visual states also remain unverified. The observations above establish behavior for the specified fixtures and widths, not a real workshop pilot.

## Verdict

**Approve for the reviewed source and tested dashboard flow.** No HIGH or MEDIUM finding remains in that scope. Native 200% zoom, screen reader, and the listed untested visual states remain separate checks before claiming full accessibility coverage.
