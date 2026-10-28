# RosterOps — Smart Roster Management System

A Streamlit MVP for the DataStraw Tech Internship assessment. It includes fictional sample data for 30 employees, 12 brands, five pods, process allocations, monthly draft generation, leave/holiday configuration, filtered roster views, CSV export, and baseline coverage-gap validation.

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## How to use

1. Open the app in your browser.
2. Review the fictional employee, brand, and allocation data.
3. Configure approved leave and public holidays in the relevant tab.
4. Select a month and year in the sidebar and click **Generate / regenerate roster**.
5. Review the roster in company, pod, brand, process, or employee views.
6. Review all flagged coverage gaps under **Validation**.
7. Export the generated draft as CSV.

## Data model

- **Employee**: employee ID, name, pod, weekly-off day, active flag.
- **Brand**: brand ID, brand name, pod, operating-calendar rule.
- **Allocation**: brand, employee, process, minimum staffing field.
- **Leave/unavailability**: employee, date, type, approval status.
- **Holiday**: date and holiday name.
- **Roster entry**: date, pod, brand, process, employee, status and reason.

Allocations form the relationship between employees, brands, and processes. A person may have multiple allocations; a brand may have one or multiple people. The sample has 10 single-resource brands and two multi-resource brands.

## Scheduling approach and limitations

The baseline generator iterates through every date in the selected month and each configured allocation. It checks the brand's operating calendar, employee active status, weekly off, and approved leave. Unavailable allocations are explicitly marked `COVERAGE GAP` and added to the validation issue list rather than silently treated as covered.

This is an assessment MVP, not a production scheduling optimizer. The current baseline does **not** implement shift-level overlap checks, automatic backup assignment, global minimum-coverage aggregation for multiple workers on a shared process, preference optimization, persistent database storage, authentication, concurrent editing, or formal approval/publishing. Changes made in the UI persist only for the current app session. These are important next steps before real operational use.

## Important assumptions

- Sample names and brands are fictional.
- Each allocation is treated as a required process-day assignment when the brand is open.
- The current UI's `min_staff` field is stored as configuration but is not yet used in aggregate multi-person coverage optimization.
- The operating-calendar examples are simplified to 365 days, public holidays off, and Sundays plus public holidays off.
- This app is a draft planner; a manager must review all issues before treating any roster as ready.

## Suggested next improvements

1. Add a persistent relational database and migrations.
2. Implement process/day minimum coverage and distinct employee counting.
3. Add shift windows and double-booking checks across all allocations.
4. Add backup recommendations and fair-off optimization using a constraint solver.
5. Add roster change-impact preview, audit history, approvals, and role-based access.
6. Add automated tests and CI before production deployment.

## Tell us how you think

1. **How are entities modeled?** Employees, brands, and pods are independent entities. Allocations associate an employee with a brand and process. Operating calendars belong to brands in this MVP; a production model should support rules at both brand and process level.
2. **How is a roster generated and checked?** The generator walks through the selected month and each allocation, skips dates when the brand is closed, and checks whether the allocated employee is active and available. Unavailable assignments are recorded as gaps.
3. **Single-resource vs multi-resource brands?** The allocation table supports both. A single-resource brand has one employee linked to its processes; a multi-resource brand can split processes or assign multiple employees to the same process.
4. **What if the only employee is unavailable?** The allocation is marked as a coverage gap, the reason is displayed, and the manager is prompted to assign an eligible backup or change the approved schedule.
5. **Conflicts or insufficient staffing?** The baseline surfaces unavailable allocations. A production version should aggregate required staffing by brand/process/date and explain infeasible constraint sets.
6. **What is automated vs human-controlled?** Draft creation and baseline checks are automated. Approval, exception resolution, and operational judgment remain with the manager.
7. **What changes if the team doubles?** Use a relational database, indexed queries, a separate scheduling service, explicit constraint models, background jobs for large solves, automated tests, and role-based access controls.
8. **What would be improved with another week?** Implement process-level coverage aggregation and overlap checks first, then a constraint solver, persistent storage, test coverage, and audit-friendly change previews.

## Deployment

Deploy to a Python-compatible host that supports Streamlit. Set the app entry point to `app.py` and install `requirements.txt`. Verify the public URL in a private/incognito browser before submitting. The app has not been deployed by this package; add your actual working URL and GitHub repository to the submission email only after verifying them.
