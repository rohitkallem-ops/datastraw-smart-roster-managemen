import calendar
from datetime import date, timedelta
import pandas as pd
import streamlit as st

st.set_page_config(page_title="RosterOps | Smart Roster Management", page_icon="📅", layout="wide")

# Demo data is intentionally fictional and can be edited in the UI.
PROCESSES = ["Customer Support", "Abandoned Cart Conversion", "Retention", "NDR Management"]
PODS = ["North Pod", "South Pod", "East Pod", "West Pod", "Central Pod"]

@st.cache_data
def seed_data():
    employees = pd.DataFrame([
        {"employee_id": f"E{i:03d}", "name": f"Employee {i:02d}", "pod": PODS[(i-1)%len(PODS)], "weekly_off": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][(i-1)%7], "active": True}
        for i in range(1, 31)
    ])
    brands = []
    for i in range(1, 13):
        brands.append({"brand_id": f"B{i:02d}", "brand": f"Brand {chr(64+i)}", "pod": PODS[(i-1)%len(PODS)], "calendar": ["365 days", "Public holidays off", "Sundays and public holidays off"][(i-1)%3]})
    brands = pd.DataFrame(brands)
    allocations = []
    # Ten of twelve brands are single-resource brands; two use multiple resources.
    for i in range(1, 11):
        eid = f"E{i:03d}"
        for proc in PROCESSES[:(2 if i % 2 else 3)]:
            allocations.append({"brand_id": f"B{i:02d}", "employee_id": eid, "process": proc, "min_staff": 1})
    for proc, eid in zip(PROCESSES, ["E011", "E012", "E013", "E014"]):
        allocations.append({"brand_id": "B11", "employee_id": eid, "process": proc, "min_staff": 1})
    for proc, eids in [("Customer Support", ["E015", "E016"]), ("Abandoned Cart Conversion", ["E017"]), ("NDR Management", ["E018", "E019"])]:
        for eid in eids:
            allocations.append({"brand_id": "B12", "employee_id": eid, "process": proc, "min_staff": 1})
    return employees, brands, pd.DataFrame(allocations), pd.DataFrame(columns=["employee_id", "date", "type", "status"]), pd.DataFrame(columns=["date", "name"])

if "employees" not in st.session_state:
    e, b, a, l, h = seed_data()
    st.session_state.update(employees=e, brands=b, allocations=a, leaves=l, holidays=h, roster=None, conflicts=[])

st.title("📅 RosterOps")
st.caption("Smart Roster Management System · DataStraw internship assessment · Fictional demo dataset")

with st.sidebar:
    st.header("Roster settings")
    today = date.today()
    year = st.number_input("Year", min_value=2024, max_value=2035, value=today.year, step=1)
    month = st.selectbox("Month", list(range(1, 13)), index=today.month-1, format_func=lambda x: calendar.month_name[x])
    st.divider()
    st.metric("Employees", len(st.session_state.employees))
    st.metric("Brands", len(st.session_state.brands))
    st.metric("Resource allocations", len(st.session_state.allocations))
    st.caption("Sample records are fictional. Configure the data before using this for real operations.")

pages = st.tabs(["Overview", "Generate roster", "Roster views", "Team & allocations", "Leave & holidays", "Validation"])

with pages[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Employees", len(st.session_state.employees))
    c2.metric("Brands", len(st.session_state.brands))
    c3.metric("Processes", len(PROCESSES))
    c4.metric("Pods", st.session_state.employees.pod.nunique())
    st.subheader("Operational model")
    st.write("Manage employees, brands, processes, pods, working calendars and resource allocations. Generate a monthly draft, inspect coverage gaps, then make changes before publishing.")
    st.info("Scheduling policy: mandatory availability and coverage constraints take precedence over weekly-off preferences. Unresolved gaps are surfaced for manager review.")
    st.subheader("Brand operating calendars")
    st.dataframe(st.session_state.brands, use_container_width=True, hide_index=True)

with pages[1]:
    st.subheader(f"Generate monthly roster · {calendar.month_name[int(month)]} {int(year)}")
    st.write("The baseline generator creates draft assignments, respects employee weekly offs, approved leave and each brand's operating calendar, and records coverage gaps.")
    if st.button("Generate / regenerate roster", type="primary"):
        employees = st.session_state.employees.copy()
        brands = st.session_state.brands.set_index("brand_id").to_dict("index")
        allocations = st.session_state.allocations.copy()
        leaves = st.session_state.leaves.copy()
        holidays = set(st.session_state.holidays.date.astype(str)) if not st.session_state.holidays.empty else set()
        _, ndays = calendar.monthrange(int(year), int(month))
        dates = [date(int(year), int(month), d) for d in range(1, ndays+1)]
        rows, conflicts = [], []
        # Track which brand each employee is covering each day. An employee may
        # cover several processes for the same brand, but is not assigned to two brands.
        employee_brand_by_day = {}

        def unavailable_reason(emp, day, weekday):
            if not bool(emp.active):
                return "inactive employee"
            if str(emp.weekly_off) == weekday:
                return "weekly off"
            if not leaves.empty:
                matches = leaves[(leaves.employee_id == emp.employee_id) & (leaves.date.astype(str) == day.isoformat()) & (leaves.status == "Approved")]
                if not matches.empty:
                    return "approved leave"
            return ""

        for day in dates:
            for _, alloc in allocations.iterrows():
                brand = brands.get(alloc.brand_id)
                if not brand:
                    continue
                weekday = day.strftime("%A")
                is_holiday = day.isoformat() in holidays
                calendar_rule = brand["calendar"]
                brand_operates = (calendar_rule == "365 days" or (calendar_rule == "Public holidays off" and not is_holiday) or (calendar_rule == "Sundays and public holidays off" and weekday != "Sunday" and not is_holiday))
                if not brand_operates:
                    continue

                primary_rows = employees[employees.employee_id == alloc.employee_id]
                if primary_rows.empty:
                    conflicts.append({"date": day.isoformat(), "brand": brand["brand"], "process": alloc.process, "severity": "Critical", "issue": f"Allocated employee {alloc.employee_id} does not exist", "suggestion": "Correct or remove the allocation."})
                    rows.append({"date": day, "weekday": weekday, "pod": brand["pod"], "brand": brand["brand"], "process": alloc.process, "employee_id": alloc.employee_id, "employee": "Unknown employee", "status": "COVERAGE GAP", "reason": "invalid allocation"})
                    continue

                primary = primary_rows.iloc[0]
                reason = unavailable_reason(primary, day, weekday)
                primary_key = (str(primary.employee_id), day.isoformat())
                already_on_other_brand = primary_key in employee_brand_by_day and employee_brand_by_day[primary_key] != brand["brand"]
                if not reason and already_on_other_brand:
                    reason = "already assigned to another brand"

                selected = None
                if not reason:
                    selected = primary
                else:
                    # Backup policy: prefer active, available employees in the same pod.
                    # Do not silently double-book someone across brands on the same date.
                    pool = employees[(employees.pod == brand["pod"]) & (employees.active == True)].copy()
                    pool = pool[pool.employee_id != primary.employee_id]
                    pool = pool.sort_values("employee_id")
                    for _, backup in pool.iterrows():
                        backup_reason = unavailable_reason(backup, day, weekday)
                        backup_key = (str(backup.employee_id), day.isoformat())
                        if backup_reason:
                            continue
                        if backup_key in employee_brand_by_day and employee_brand_by_day[backup_key] != brand["brand"]:
                            continue
                        selected = backup
                        break

                if selected is not None:
                    selected_key = (str(selected.employee_id), day.isoformat())
                    employee_brand_by_day[selected_key] = brand["brand"]
                    is_backup = str(selected.employee_id) != str(primary.employee_id)
                    rows.append({"date": day, "weekday": weekday, "pod": brand["pod"], "brand": brand["brand"], "process": alloc.process, "employee_id": selected.employee_id, "employee": selected.name, "status": "Backup assigned" if is_backup else "Assigned", "reason": f"Backup for {primary.employee_id} ({reason})" if is_backup else ""})
                    if is_backup:
                        conflicts.append({"date": day.isoformat(), "brand": brand["brand"], "process": alloc.process, "severity": "Medium", "issue": f"Primary employee {primary.employee_id} unavailable ({reason}); backup {selected.employee_id} assigned from {brand['pod']}", "suggestion": "Review backup eligibility and confirm the assignment with the operations manager."})
                else:
                    conflicts.append({"date": day.isoformat(), "brand": brand["brand"], "process": alloc.process, "severity": "High", "issue": f"No eligible same-pod backup available; primary {primary.employee_id} unavailable ({reason or 'already assigned to another brand'})", "suggestion": "Assign an eligible backup or change the approved schedule."})
                    rows.append({"date": day, "weekday": weekday, "pod": brand["pod"], "brand": brand["brand"], "process": alloc.process, "employee_id": primary.employee_id, "employee": primary.name, "status": "COVERAGE GAP", "reason": reason or "already assigned to another brand"})
        st.session_state.roster = pd.DataFrame(rows)
        st.session_state.conflicts = conflicts
        st.success(f"Draft generated: {len(rows)} process-day records and {len(conflicts)} flagged issue(s). Review Validation before publishing.")
    if st.session_state.roster is not None:
        r = st.session_state.roster
        st.dataframe(r.head(1000), use_container_width=True, hide_index=True)
        st.download_button("Download roster CSV", r.to_csv(index=False).encode("utf-8"), file_name=f"roster_{year}_{month:02d}.csv", mime="text/csv")

with pages[2]:
    st.subheader("Roster views")
    if st.session_state.roster is None:
        st.warning("Generate a roster first.")
    else:
        r = st.session_state.roster.copy()
        view = st.selectbox("View by", ["Company-wide", "Pod", "Brand", "Process", "Employee"])
        colmap = {"Company-wide": None, "Pod": "pod", "Brand": "brand", "Process": "process", "Employee": "employee"}
        col = colmap[view]
        if col:
            values = sorted(r[col].dropna().unique().tolist())
            chosen = st.selectbox(f"Select {col.lower()}", values)
            r = r[r[col] == chosen]
        st.dataframe(r, use_container_width=True, hide_index=True)
        gaps = int((r.status == "COVERAGE GAP").sum())
        st.metric("Coverage gaps in current view", gaps)

with pages[3]:
    st.subheader("Employees")
    st.caption("Edit the table and click Save changes. Employee IDs must remain unique.")
    edited = st.data_editor(st.session_state.employees, use_container_width=True, num_rows="dynamic", key="employee_editor", disabled=["employee_id"])
    if st.button("Save employee changes"):
        if edited.employee_id.duplicated().any():
            st.error("Employee IDs must be unique. Changes were not saved.")
        else:
            st.session_state.employees = edited
            st.success("Employee table updated for this session.")
    st.subheader("Brands")
    bedited = st.data_editor(st.session_state.brands, use_container_width=True, num_rows="dynamic", key="brand_editor", disabled=["brand_id"])
    if st.button("Save brand changes"):
        if bedited.brand_id.duplicated().any():
            st.error("Brand IDs must be unique. Changes were not saved.")
        else:
            st.session_state.brands = bedited
            st.success("Brand table updated for this session.")
    st.subheader("Resource allocations")
    aedited = st.data_editor(st.session_state.allocations, use_container_width=True, num_rows="dynamic", key="allocation_editor")
    if st.button("Save allocation changes"):
        valid_emp = set(st.session_state.employees.employee_id)
        valid_brand = set(st.session_state.brands.brand_id)
        bad = aedited[~aedited.employee_id.isin(valid_emp) | ~aedited.brand_id.isin(valid_brand) | ~aedited.process.isin(PROCESSES)]
        if not bad.empty:
            st.error("Some allocations reference an unknown employee, brand or process. Changes were not saved.")
        else:
            st.session_state.allocations = aedited
            st.success("Allocations updated for this session. Regenerate the roster to apply changes.")

with pages[4]:
    st.subheader("Planned leave and comp-off")
    emp_options = st.session_state.employees.employee_id.tolist()
    with st.form("leave_form"):
        employee_id = st.selectbox("Employee", emp_options)
        leave_date = st.date_input("Date", value=date(int(year), int(month), 1))
        leave_type = st.selectbox("Type", ["Planned leave", "Comp-off", "Other unavailability"])
        leave_status = st.selectbox("Status", ["Pending", "Approved", "Rejected"], index=1)
        submitted = st.form_submit_button("Add leave / unavailability")
    if submitted:
        new = pd.DataFrame([{"employee_id": employee_id, "date": leave_date.isoformat(), "type": leave_type, "status": leave_status}])
        st.session_state.leaves = pd.concat([st.session_state.leaves, new], ignore_index=True)
        st.success("Entry added. Regenerate the roster to recalculate coverage.")
    st.dataframe(st.session_state.leaves, use_container_width=True, hide_index=True)
    st.subheader("Public holidays")
    with st.form("holiday_form"):
        hol_date = st.date_input("Holiday date", value=date(int(year), int(month), 1), key="holiday_date")
        hol_name = st.text_input("Holiday name", value="Configured holiday")
        hol_submit = st.form_submit_button("Add holiday")
    if hol_submit:
        newh = pd.DataFrame([{"date": hol_date.isoformat(), "name": hol_name}])
        st.session_state.holidays = pd.concat([st.session_state.holidays, newh], ignore_index=True)
        st.success("Holiday added. Regenerate the roster to recalculate coverage.")
    st.dataframe(st.session_state.holidays, use_container_width=True, hide_index=True)

with pages[5]:
    st.subheader("Validation and conflict review")
    if st.session_state.roster is None:
        st.warning("Generate a roster first. Validation results will appear here.")
    else:
        r = st.session_state.roster
        gaps = r[r.status == "COVERAGE GAP"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Process-day records", len(r))
        c2.metric("Coverage gaps", len(gaps))
        c3.metric("Assigned records", int((r.status == "Assigned").sum()))
        if len(gaps):
            st.error("Coverage gaps need review before the roster can be considered ready.")
            st.dataframe(gaps, use_container_width=True, hide_index=True)
        else:
            st.success("No coverage gaps were detected by the baseline checks for this generated draft.")
        if st.session_state.conflicts:
            st.subheader("Issues and suggested next actions")
            st.dataframe(pd.DataFrame(st.session_state.conflicts), use_container_width=True, hide_index=True)
        st.caption("This MVP validates assigned employee availability and coverage gaps. It does not yet implement shift-level overlap checks, automatic backup optimization, persistent multi-user storage, authentication, or a formal publish/approval workflow. Do not use it as a production roster without extending and testing these controls.")
