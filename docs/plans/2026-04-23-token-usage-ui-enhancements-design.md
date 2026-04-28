# Token Usage UI Enhancements Design

## Goal
Enhance the Token Usage Statistics tool with better unit readability, chart switching, dynamic time ranges, and table pagination.

## Changes
1. **Token Unit Formatting**: Switch from `K/M` to Chinese units `万/百万/千万/亿`.
2. **Chart Type Toggle**: Add a switch between `Bar Chart` (stacked + cost line) and `Line Chart` (trend lines).
3. **Dynamic Time Range**: Adjust time range dropdown options based on the selected dimension (Day/Week/Month).
4. **Table Pagination**: Introduce pagination for the data table to handle larger datasets cleanly.

## UI Layout
- **Filters**: Tool | Dimension | Time Range | Chart Type | Refresh
- **Stats Cards**: Total Cost | Total Tokens (亿) | Input (亿) | Output (千万) | Avg Daily Cost ($)
- **Charts**: Toggle between stacked bars+line and multi-line chart.
- **Data Table**: Sorted columns with pagination controls (10/20/50 per page).
