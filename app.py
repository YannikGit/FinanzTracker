import streamlit as st
import pandas as pd
import plotly.express as px
import os
from core.storage import load_transactions, save_transactions
from core.analysis import to_dataframe
from core.visualizer import (
    plot_by_category, plot_by_month,
    plot_pie_category, plot_over_time,
    plot_income_vs_expenses
)
from core.importer import import_all_pdfs
from core.receipt_importer import import_all_receipts
from core.receipt_storage import load_receipts
from core.category_manager import (
    load_category_tree, save_category_tree,
    load_store_categories, save_store_categories,
    add_top_category, add_subcategory
)
from core.profile_manager import (
    load_profiles, get_active_profile,
    set_active_profile, create_profile, delete_profile
)
from core.erstattung_manager import (
    load_rules, add_rule, delete_rule,
    toggle_rule, apply_rules, get_latest_erstattung_amount
)

st.set_page_config(
    page_title="FinanzTracker",
    page_icon="💰",
    layout="wide"
)

st.title("💰 FinanzTracker")

# --- PROFILE SWITCHER ---
profiles = load_profiles()
active_profile = get_active_profile()

with st.sidebar:
    st.title("👤 Profil")
    selected_profile = st.selectbox(
        "Aktives Profil",
        options=profiles,
        index=profiles.index(active_profile) if active_profile in profiles else 0,
        key="profile_selector"
    )
    if selected_profile != active_profile:
        set_active_profile(selected_profile)
        st.rerun()

    st.markdown("---")
    st.markdown("#### ➕ Neues Profil")
    new_profile_name = st.text_input("Profilname", key="new_profile_name")
    if st.button("Profil erstellen"):
        if new_profile_name.strip():
            create_profile(new_profile_name.strip())
            set_active_profile(new_profile_name.strip())
            st.success(f"Profil '{new_profile_name}' erstellt!")
            st.rerun()
        else:
            st.error("Bitte einen Namen eingeben.")

    st.markdown("---")
    st.markdown("#### 🗑️ Profil löschen")
    if len(profiles) > 1:
        profile_to_delete = st.selectbox(
            "Profil auswählen",
            options=[p for p in profiles if p != active_profile],
            key="delete_profile_select"
        )
        if st.button("🗑️ Profil löschen", type="secondary"):
            if delete_profile(profile_to_delete):
                st.success(f"Profil '{profile_to_delete}' gelöscht!")
                st.rerun()
    else:
        st.caption("⚠️ Letztes Profil kann nicht gelöscht werden.")

    st.markdown("---")
    st.caption(f"Aktiv: **{active_profile}**")

# --- GLOBAL CONSTANTS ---
month_names = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
}
month_names_reverse = {v: k for k, v in month_names.items()}

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard",
    "📋 Transaktionen",
    "📈 Analyse",
    "📥 Import",
    "⚙️ Einstellungen"
])

# --- LOAD DATA ONCE ---
all_transactions = load_transactions()
df = to_dataframe(all_transactions) if all_transactions else None

# ==========================================
# TAB 1 — DASHBOARD
# ==========================================
with tab1:
    if df is None:
        st.warning("Keine Transaktionen gefunden. Bitte zuerst PDFs importieren!")
    else:
        st.subheader("Übersicht")

        # Exclude fully reimbursed transactions from all calculations
        active_df = df[~df["reimbursement_status"].isin(["full_rule", "full_oneoff"])].copy()
        active_df["amount"] = active_df["effective_amount"]

        num_months = active_df["date"].dt.to_period("M").nunique()
        if num_months == 0:
            num_months = 1

        avg_einnahmen = active_df[active_df["type"] == "Einnahme"]["amount"].sum() / num_months
        avg_ausgaben = abs(active_df[active_df["type"] == "Ausgabe"]["amount"].sum()) / num_months
        avg_differenz = avg_einnahmen - avg_ausgaben

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💚 Ø Einnahmen / Monat", f"{avg_einnahmen:.2f}€")
        with col2:
            st.metric("🔴 Ø Ausgaben / Monat", f"{avg_ausgaben:.2f}€")
        with col3:
            st.metric("💰 Ø Differenz / Monat", f"{avg_differenz:.2f}€",
                      delta=f"{avg_differenz:.2f}€")

        st.markdown("---")

        # --- CATEGORY AVERAGES ---
        st.subheader("📂 Ø Ausgaben pro Kategorie / Monat")
        ausgaben_df = active_df[active_df["type"] == "Ausgabe"].copy()

        top_cat_avg = (
            ausgaben_df.groupby("top_category")["amount"]
            .sum().abs() / num_months
        ).round(2).sort_values(ascending=False)

        top_cats = top_cat_avg.index.tolist()
        for i in range(0, len(top_cats), 3):
            cols = st.columns(3)
            for j, cat in enumerate(top_cats[i:i+3]):
                with cols[j]:
                    st.metric(f"📁 {cat}", f"{top_cat_avg[cat]:.2f}€ / Monat")

        st.markdown("---")

        # --- SUBCATEGORY AVERAGES ---
        st.subheader("🔍 Unterkategorien")
        for top_cat in top_cats:
            sub_df = ausgaben_df[ausgaben_df["top_category"] == top_cat]
            sub_avg = (
                sub_df.groupby("sub_category")["amount"]
                .sum().abs() / num_months
            ).round(2).sort_values(ascending=False)

            adj_top_total = sub_avg.sum()

            with st.expander(f"📁 {top_cat} — Ø {adj_top_total:.2f}€ / Monat"):
                if not sub_avg.empty:
                    sub_cols = st.columns(min(len(sub_avg), 3))
                    for i, (sub, val) in enumerate(sub_avg.items()):
                        with sub_cols[i % 3]:
                            st.metric(f"• {sub}", f"{val:.2f}€ / Monat")

        st.markdown("---")

        # --- REIMBURSEMENT RULES SUMMARY ---
        from core.reimbursement_manager import load_reimbursement_rules
        reimb_rules = load_reimbursement_rules()
        active_rules = [r for r in reimb_rules if r["active"]]

        if active_rules:
            st.subheader("💸 Aktive Erstattungsregeln")
            for rule in active_rules:
                total = sum(d["amount"] for d in rule["deductions"])
                cols = st.columns(len(rule["deductions"]) + 2)
                with cols[0]:
                    st.metric("💰 Store", rule["income_store"])
                for i, d in enumerate(rule["deductions"]):
                    with cols[i + 1]:
                        st.metric(
                            f"↩️ {d['sub_category']}",
                            f"-{d['amount']:.2f}€",
                            delta_color="off"
                        )
                with cols[-1]:
                    st.metric("Gesamt Abzug", f"-{total:.2f}€", delta_color="off")
            st.markdown("---")

        # --- CHARTS ---
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(plot_by_category(active_df), width='stretch', key="dash_cat")
        with col2:
            st.plotly_chart(plot_pie_category(active_df), width='stretch', key="dash_pie")

        st.plotly_chart(plot_over_time(active_df), width='stretch', key="dash_time")
        
# ==========================================
# TAB 2 — TRANSAKTIONEN
# ==========================================
with tab2:
    if df is None:
        st.warning("Keine Transaktionen gefunden.")
    else:
        st.subheader("Transaktionen")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            available_years = sorted(df["year"].unique().tolist())
            selected_year = st.selectbox("Jahr", ["Alle"] + available_years, key="t_year")
        with col2:
            available_months = sorted(df["month"].unique().tolist())
            selected_month = st.selectbox("Monat", ["Alle"] + [month_names[m] for m in available_months], key="t_month")
        with col3:
            selected_type = st.selectbox("Typ", ["Alle", "Ausgaben", "Einnahmen"], key="t_type")
        with col4:
            available_cats = sorted(df["top_category"].dropna().unique().tolist())
            selected_cat = st.selectbox("Kategorie", ["Alle"] + available_cats, key="t_cat")

        # Show/hide reimbursed toggle
        show_reimbursed = st.toggle(
            "👻 Erstattete Transaktionen anzeigen",
            value=True,
            key="show_reimbursed"
        )

        table_df = df.copy()
        if selected_year != "Alle":
            table_df = table_df[table_df["year"] == selected_year]
        if selected_month != "Alle":
            table_df = table_df[table_df["month"] == month_names_reverse[selected_month]]
        if selected_type == "Ausgaben":
            table_df = table_df[table_df["type"] == "Ausgabe"]
        elif selected_type == "Einnahmen":
            table_df = table_df[table_df["type"] == "Einnahme"]
        if selected_cat != "Alle":
            table_df = table_df[table_df["top_category"] == selected_cat]

        sort_by = st.selectbox("Sortieren nach", ["Datum", "Betrag", "Store", "Kategorie"], key="t_sort")
        sort_map = {"Datum": "date", "Betrag": "amount", "Store": "store", "Kategorie": "sub_category"}
        table_df = table_df.sort_values(sort_map[sort_by], ascending=False)

        # Summary banner — uses effective amounts, excludes fully reimbursed
        active_df = table_df[~table_df["reimbursement_status"].isin(["full_rule", "full_oneoff"])]
        st.markdown("---")
        total_in_filtered = active_df[active_df["type"] == "Einnahme"]["effective_amount"].sum()
        total_out_filtered = abs(active_df[active_df["type"] == "Ausgabe"]["effective_amount"].sum())
        total_diff_filtered = total_in_filtered - total_out_filtered

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🔢 Transaktionen", len(active_df))
        with col2:
            st.metric("💚 Einnahmen", f"{total_in_filtered:.2f}€")
        with col3:
            st.metric("🔴 Ausgaben", f"{total_out_filtered:.2f}€")
        with col4:
            st.metric("💰 Differenz", f"{total_diff_filtered:.2f}€",
                      delta=f"{total_diff_filtered:.2f}€")
        st.markdown("---")

        edit_mode = st.toggle("✏️ Bearbeitungsmodus", value=False, key="edit_mode")

        if not edit_mode:
            # Build display dataframe
            display_rows = []
            for _, row in table_df.iterrows():
                status = row.get("reimbursement_status")
                is_fully_reimbursed = status in ("full_rule", "full_oneoff")
                is_partially_reimbursed = status in ("partial_rule", "partial_oneoff")

                # Skip fully reimbursed if toggle is off
                if is_fully_reimbursed and not show_reimbursed:
                    continue

                # Format amount display
                eff = row["effective_amount"]
                orig = row["amount"]

                if is_fully_reimbursed:
                    amount_display = f"0.00€ ({orig:.2f}€)"
                elif is_partially_reimbursed:
                    amount_display = f"{eff:.2f}€ ({orig:.2f}€) ↓"
                else:
                    amount_display = f"{eff:.2f}€"

                display_rows.append({
                    "Datum": row["date"].strftime("%d.%m.%Y"),
                    "Store": row["store"],
                    "Betrag": amount_display,
                    "Kategorie": row["top_category"],
                    "Unterkategorie": row["sub_category"],
                    "_status": status,
                    "_amount": eff
                })

            display_df = pd.DataFrame(display_rows)

            if display_df.empty:
                st.info("Keine Transaktionen gefunden.")
            else:
                # Style the dataframe
                # Style using helper columns, then display without them
                def style_row(row):
                    status = row["_status"]
                    if status in ("full_rule", "full_oneoff"):
                        return ["color: #aaaaaa; font-style: italic"] * len(row)
                    elif status in ("partial_rule", "partial_oneoff"):
                        color = "color: green" if row["_amount"] > 0 else "color: #cc6600"
                        return [color if col == "Betrag" else "" for col in row.index]
                    else:
                        color = "color: green" if row["_amount"] > 0 else "color: red"
                        return [color if col == "Betrag" else "" for col in row.index]

                # Get styles as a list of dicts
                styles = display_df.apply(style_row, axis=1).tolist()

                # Create clean display df without helper columns
                clean_df = display_df[["Datum", "Store", "Betrag", "Kategorie", "Unterkategorie"]].copy()

                # Reapply styles to clean df
                def style_clean_row(row):
                    idx = row.name
                    full_row = display_df.loc[idx]
                    status = full_row["_status"]
                    if status in ("full_rule", "full_oneoff"):
                        return ["color: #aaaaaa; font-style: italic"] * len(row)
                    elif status in ("partial_rule", "partial_oneoff"):
                        color = "color: green" if full_row["_amount"] > 0 else "color: #cc6600"
                        return [color if col == "Betrag" else "" for col in row.index]
                    else:
                        color = "color: green" if full_row["_amount"] > 0 else "color: red"
                        return [color if col == "Betrag" else "" for col in row.index]

                styled = clean_df.style.apply(style_clean_row, axis=1)
                st.dataframe(styled, width='stretch', height=500)
        else:
            st.info("✏️ Bearbeitungsmodus aktiv — bearbeite Transaktionen direkt in der Tabelle.")

            tree = load_category_tree()
            top_categories = list(tree.keys())
            all_subcategories = sorted(list(set(
                sub for data in tree.values()
                for sub in data["subcategories"]
            )))

            edit_df = table_df[["date", "store", "amount", "top_category", "sub_category"]].copy()
            edit_df["date"] = edit_df["date"].dt.strftime("%d.%m.%Y")
            edit_df["delete"] = False
            edit_df.columns = ["Datum", "Store", "Betrag (€)", "Kategorie", "Unterkategorie", "🗑️ Löschen"]

            edited = st.data_editor(
                edit_df,
                height=500,
                use_container_width=True,
                column_config={
                    "Datum": st.column_config.TextColumn("Datum"),
                    "Store": st.column_config.TextColumn("Store"),
                    "Betrag (€)": st.column_config.NumberColumn("Betrag (€)", format="%.2f"),
                    "Kategorie": st.column_config.SelectboxColumn("Kategorie", options=top_categories),
                    "Unterkategorie": st.column_config.SelectboxColumn("Unterkategorie", options=all_subcategories),
                    "🗑️ Löschen": st.column_config.CheckboxColumn("🗑️ Löschen")
                },
                hide_index=True,
                key="editable_table"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Änderungen speichern", type="primary"):
                    to_delete = set()
                    for _, row in edited.iterrows():
                        key = f"{row['Datum']}_{row['Store']}_{row['Betrag (€)']}"
                        if row["🗑️ Löschen"]:
                            to_delete.add(key)

                    updated_transactions = []
                    for t in all_transactions:
                        date_str = t["date"] if isinstance(t["date"], str) else t["date"].strftime("%d.%m.%Y")
                        key = f"{date_str}_{t['store']}_{t['amount']}"
                        if key in to_delete:
                            continue
                        matching_rows = edited[
                            (edited["Datum"] == date_str) &
                            (edited["Store"] == t["store"]) &
                            (edited["Betrag (€)"] == t["amount"])
                        ]
                        if not matching_rows.empty:
                            row = matching_rows.iloc[0]
                            t["store"] = row["Store"]
                            t["amount"] = float(row["Betrag (€)"])
                            t["date"] = row["Datum"]
                            t["top_category"] = row["Kategorie"]
                            t["sub_category"] = row["Unterkategorie"]
                        updated_transactions.append(t)

                    save_transactions(updated_transactions)
                    deleted_count = len(all_transactions) - len(updated_transactions)
                    st.success(f"✅ Gespeichert! {deleted_count} Transaktion(en) gelöscht.")
                    st.rerun()

            with col2:
                to_delete_count = edited["🗑️ Löschen"].sum()
                if to_delete_count > 0:
                    st.warning(f"⚠️ {to_delete_count} Transaktion(en) zum Löschen markiert.")

        # --- ONE-OFF REIMBURSEMENT LINKING ---
        st.markdown("---")
        st.markdown("### 🔗 Einmalige Erstattung verknüpfen")
        st.write("Verknüpfe eine Einnahme mit einer Ausgabe als einmalige Erstattung.")

        from core.reimbursement_manager import link_one_off_reimbursement, unlink_reimbursement
        from core.models import make_id

        # Get all income transactions
        income_transactions = [
            t for t in all_transactions
            if t["amount"] > 0
            and t.get("reimbursement_status") is None
        ]
        expense_transactions = [
            t for t in all_transactions
            if t["amount"] < 0
            and t.get("reimbursement_status") is None
        ]

        if not income_transactions or not expense_transactions:
            st.info("Keine unverstatteten Transaktionen verfügbar.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                income_options = {
                    f"{t['store']} | +{t['amount']:.2f}€ | {t['date']}": make_id(t)
                    for t in sorted(income_transactions, key=lambda x: x["date"], reverse=True)
                }
                selected_income = st.selectbox(
                    "💚 Einnahme (Erstattung)",
                    options=list(income_options.keys()),
                    key="oneoff_income"
                )

            with col2:
                expense_options = {
                    f"{t['store']} | {t['amount']:.2f}€ | {t['date']}": make_id(t)
                    for t in sorted(expense_transactions, key=lambda x: x["date"], reverse=True)
                }
                selected_expense = st.selectbox(
                    "🔴 Ausgabe (erstattet)",
                    options=list(expense_options.keys()),
                    key="oneoff_expense"
                )

            # Get the selected income amount as default
            selected_income_id = income_options[selected_income]
            selected_income_t = next(
                t for t in all_transactions if make_id(t) == selected_income_id
            )
            selected_expense_id = expense_options[selected_expense]
            selected_expense_t = next(
                t for t in all_transactions if make_id(t) == selected_expense_id
            )

            reimb_amount = st.number_input(
                "Erstattungsbetrag (€)",
                min_value=0.01,
                max_value=float(abs(selected_expense_t["amount"])),
                value=min(float(selected_income_t["amount"]),
                         float(abs(selected_expense_t["amount"]))),
                step=0.01,
                key="oneoff_amount"
            )

            new_expense = round(abs(selected_expense_t["amount"]) - reimb_amount, 2)
            remaining_income = round(selected_income_t["amount"] - reimb_amount, 2)

            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"Ausgabe nach Erstattung: **{new_expense:.2f}€**"
                          f" {'(vollständig erstattet)' if new_expense == 0 else ''}")
            with col2:
                st.caption(f"Verbleibende Einnahme: **{remaining_income:.2f}€**"
                          f" {'(vollständig verwendet)' if remaining_income == 0 else ''}")

            if st.button("🔗 Verknüpfung erstellen", type="primary"):
                success, msg = link_one_off_reimbursement(
                    selected_income_id,
                    selected_expense_id,
                    reimb_amount
                )
                if success:
                    st.success("✅ Verknüpfung erstellt!")
                    st.rerun()
                else:
                    st.error(f"Fehler: {msg}")

        # --- UNLINK REIMBURSEMENTS ---
        st.markdown("---")
        st.markdown("### 🔓 Erstattung aufheben")

        linked_transactions = [
            t for t in all_transactions
            if t.get("reimbursement_status") is not None
        ]

        if not linked_transactions:
            st.info("Keine verknüpften Erstattungen vorhanden.")
        else:
            unlink_options = {
                f"{t['store']} | {t['amount']:.2f}€ | {t['date']} [{t.get('reimbursement_status')}]": make_id(t)
                for t in linked_transactions
            }
            selected_unlink = st.selectbox(
                "Verknüpfung aufheben",
                options=list(unlink_options.keys()),
                key="unlink_select"
            )
            if st.button("🔓 Verknüpfung aufheben"):
                unlink_reimbursement(unlink_options[selected_unlink])
                st.success("Verknüpfung aufgehoben!")
                st.rerun()

        # --- KASSENBON DETAILS ---
        st.markdown("---")
        st.markdown("### 🧾 Kassenbon Details")

        all_receipts = load_receipts()
        transactions_with_receipt = [
            t for t in all_transactions
            if t.get("receipt_id") is not None
        ]

        if not transactions_with_receipt:
            st.info("Noch keine Kassenbons verknüpft. Importiere Kassenbons im Import-Tab.")
        else:
            receipt_options = {
                f"{t['store']} | {t['amount']:.2f}€ | {t['date']}": t
                for t in transactions_with_receipt
            }
            selected_label = st.selectbox(
                "Transaktion mit Kassenbon auswählen",
                options=list(receipt_options.keys()),
                key="receipt_selector"
            )
            selected_transaction = receipt_options[selected_label]
            receipt_id = selected_transaction.get("receipt_id")
            matching_receipt = next(
                (r for r in all_receipts if r["receipt_id"] == receipt_id), None
            )

            if matching_receipt:
                st.markdown(
                    f"**Store:** {matching_receipt['store']} | "
                    f"**Datum:** {matching_receipt['date']} | "
                    f"**Gesamt:** {matching_receipt['total']:.2f}€"
                )
                items_df = pd.DataFrame(matching_receipt["items"])
                items_df.columns = [c.capitalize() for c in items_df.columns]
                items_df["Amount"] = items_df["Amount"].apply(lambda x: f"{x:.2f}€")

                def color_tax(val):
                    return "background-color: #fff3cd" if val == "A" else "background-color: #d4edda"

                styled_items = items_df.style.map(color_tax, subset=["Tax"])
                st.dataframe(styled_items, width='stretch')

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("🛒 Artikel gesamt", len(matching_receipt["items"]))
                with col2:
                    tax_a = sum(i["amount"] for i in matching_receipt["items"] if i["tax"] == "A")
                    st.metric("MwSt 19% (A)", f"{tax_a:.2f}€")
            else:
                st.warning("Kassenbon-Daten nicht gefunden.")

# ==========================================
# TAB 3 — ANALYSE
# ==========================================
with tab3:
    if df is None:
        st.warning("Keine Transaktionen gefunden.")
    else:
        st.subheader("📈 Analyse")

        # Exclude fully reimbursed, use effective amounts
        analyse_df = df[~df["reimbursement_status"].isin(["full_rule", "full_oneoff"])].copy()
        analyse_df["amount"] = analyse_df["effective_amount"]

        st.markdown("### Filter")
        col1, col2, col3 = st.columns(3)
        with col1:
            available_years = sorted(analyse_df["year"].unique().tolist())
            selected_year = st.selectbox("Jahr", ["Alle"] + available_years, key="a_year")
        with col2:
            available_months = sorted(analyse_df["month"].unique().tolist())
            selected_month = st.selectbox(
                "Monat", ["Alle"] + [month_names[m] for m in available_months], key="a_month"
            )
        with col3:
            available_top_cats = sorted(analyse_df["top_category"].dropna().unique().tolist())
            selected_top_cats = st.multiselect(
                "Kategorien", available_top_cats, default=available_top_cats, key="a_cats"
            )

        filtered_df = analyse_df.copy()
        if selected_year != "Alle":
            filtered_df = filtered_df[filtered_df["year"] == selected_year]
        if selected_month != "Alle":
            filtered_df = filtered_df[filtered_df["month"] == month_names_reverse[selected_month]]
        if selected_top_cats:
            filtered_df = filtered_df[filtered_df["top_category"].isin(selected_top_cats)]

        st.markdown("---")
        st.markdown("### Diagramm-Builder")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            chart_type = st.selectbox(
                "Diagrammtyp", ["Balken", "Linie", "Kreis", "Fläche"],
                key="a_chart_type"
            )
        with col2:
            transaction_type = st.selectbox(
                "Transaktionstyp", ["Ausgaben", "Einnahmen", "Beides"],
                key="a_trans_type"
            )
        with col3:
            group_by = st.selectbox(
                "Gruppieren nach",
                ["Monat", "Jahr", "Hauptkategorie", "Unterkategorie", "Store"],
                key="a_group_by"
            )
        with col4:
            top_n = st.slider(
                "Top N anzeigen", min_value=3, max_value=20, value=10, key="a_top_n"
            )

        chart_df = filtered_df.copy()
        if transaction_type == "Ausgaben":
            chart_df = chart_df[chart_df["type"] == "Ausgabe"]
            chart_df["amount"] = chart_df["amount"].abs()
        elif transaction_type == "Einnahmen":
            chart_df = chart_df[chart_df["type"] == "Einnahme"]

        group_map = {
            "Monat": "month_label", "Jahr": "year",
            "Hauptkategorie": "top_category",
            "Unterkategorie": "sub_category", "Store": "store"
        }
        chart_df["month_label"] = chart_df["date"].dt.strftime("%Y-%m")
        group_col = group_map[group_by]

        grouped = chart_df.groupby(group_col)["amount"].sum().round(2).reset_index()
        grouped.columns = [group_by, "Betrag (€)"]

        if group_by not in ["Monat", "Jahr"]:
            grouped = grouped.nlargest(top_n, "Betrag (€)")
        grouped = grouped.sort_values("Betrag (€)", ascending=False)

        color_scale = "Reds" if transaction_type == "Ausgaben" else "Greens"

        if chart_type == "Balken":
            fig = px.bar(grouped, x=group_by, y="Betrag (€)",
                         title=f"{transaction_type} nach {group_by}",
                         color="Betrag (€)", color_continuous_scale=color_scale)
        elif chart_type == "Linie":
            grouped = grouped.sort_values(group_by)
            fig = px.line(grouped, x=group_by, y="Betrag (€)",
                          title=f"{transaction_type} nach {group_by}", markers=True)
        elif chart_type == "Kreis":
            fig = px.pie(grouped, names=group_by, values="Betrag (€)",
                         title=f"{transaction_type} nach {group_by}")
        elif chart_type == "Fläche":
            grouped = grouped.sort_values(group_by)
            fig = px.area(grouped, x=group_by, y="Betrag (€)",
                          title=f"{transaction_type} nach {group_by}")

        st.plotly_chart(fig, width='stretch', key="ana_dynamic")

        st.markdown("---")
        st.markdown("### Zusammenfassung")
        st.dataframe(grouped, width='stretch')
        
# ==========================================
# TAB 4 — IMPORT
# ==========================================
with tab4:
    st.subheader("📥 PDFs importieren")

    from core.storage import get_input_dir, get_processed_dir
    from core.receipt_storage import get_receipts_input_dir

    st.markdown("### 🏦 Kontoauszüge")
    bank = st.selectbox("Bank", ["comdirect", "ing"], key="bank_select")
    uploaded_pdfs = st.file_uploader(
        "Kontoauszug PDFs hochladen", type="pdf",
        accept_multiple_files=True, key="bank_pdfs"
    )

    if uploaded_pdfs and st.button("Kontoauszüge importieren"):
        input_dir = get_input_dir()
        os.makedirs(input_dir, exist_ok=True)
        for uploaded_file in uploaded_pdfs:
            dest = os.path.join(input_dir, uploaded_file.name)
            with open(dest, "wb") as f:
                f.write(uploaded_file.getbuffer())
        with st.spinner("Importiere PDFs..."):
            import_all_pdfs(bank=bank)
        st.success(f"{len(uploaded_pdfs)} PDF(s) importiert!")
        st.rerun()

    st.markdown("---")

    st.markdown("### 🧾 Kassenbons")
    uploaded_receipts = st.file_uploader(
        "Kassenbon PDFs hochladen", type="pdf",
        accept_multiple_files=True, key="receipt_pdfs"
    )

    if uploaded_receipts and st.button("Kassenbons importieren"):
        receipt_dir = get_receipts_input_dir()
        os.makedirs(receipt_dir, exist_ok=True)
        for uploaded_file in uploaded_receipts:
            dest = os.path.join(receipt_dir, uploaded_file.name)
            with open(dest, "wb") as f:
                f.write(uploaded_file.getbuffer())
        with st.spinner("Importiere Kassenbons..."):
            import_all_receipts()
        st.success(f"{len(uploaded_receipts)} Kassenbon(s) importiert!")
        st.rerun()

    st.markdown("---")
    st.markdown("### 🏷️ Kategorisierung")

    store_categories = load_store_categories()
    updated = False
    for t in all_transactions:
        if t.get("top_category") is None and t["store"] in store_categories:
            t["top_category"] = store_categories[t["store"]]["top"]
            t["sub_category"] = store_categories[t["store"]]["sub"]
            updated = True
    if updated:
        save_transactions(all_transactions)
        all_transactions = load_transactions()

    uncategorized = [
        t for t in all_transactions
        if t.get("top_category") is None or t.get("sub_category") is None
    ]

    if not uncategorized:
        st.success("✅ Alle Transaktionen sind kategorisiert!")
    else:
        tree = load_category_tree()
        top_categories = list(tree.keys())

        seen = set()
        unique_stores = []
        for t in uncategorized:
            if t["store"] not in seen:
                seen.add(t["store"])
                unique_stores.append(t)

        st.warning(f"{len(uncategorized)} Transaktion(en) nicht kategorisiert — {len(unique_stores)} unbekannte Store(s).")

        if "cat_selections" not in st.session_state:
            st.session_state.cat_selections = {}

        for t in unique_stores:
            store = t["store"]
            st.markdown(f"**{store}** | {t['amount']:.2f}€ | {t['date']}")
            col1, col2 = st.columns(2)
            with col1:
                top = st.selectbox("Kategorie", options=top_categories, key=f"top_{store}")
            with col2:
                subs = tree.get(top, {}).get("subcategories", ["Unbekannt"])
                sub = st.selectbox("Unterkategorie", options=subs, key=f"sub_{store}")
            st.session_state.cat_selections[store] = {"top": top, "sub": sub}
            st.markdown("---")

        if st.button("✅ Kategorien speichern"):
            store_categories = load_store_categories()
            for t in all_transactions:
                store = t["store"]
                if store in st.session_state.cat_selections and (
                    t.get("top_category") is None or t.get("sub_category") is None
                ):
                    t["top_category"] = st.session_state.cat_selections[store]["top"]
                    t["sub_category"] = st.session_state.cat_selections[store]["sub"]
                    store_categories[store] = st.session_state.cat_selections[store]
            save_transactions(all_transactions)
            save_store_categories(store_categories)
            st.session_state.cat_selections = {}
            st.success("Kategorien gespeichert!")
            st.rerun()

    st.markdown("---")
    st.markdown("### ✍️ Transaktion manuell hinzufügen")
    st.write("Füge Bargeldkäufe oder andere nicht-digitale Transaktionen manuell hinzu.")

    with st.form("manual_transaction_form"):
        col1, col2 = st.columns(2)
        with col1:
            manual_date = st.date_input("Datum", key="manual_date")
            manual_store = st.text_input("Store / Beschreibung", key="manual_store")
            manual_amount = st.number_input(
                "Betrag (€) — negativ für Ausgaben, positiv für Einnahmen",
                value=-0.01,
                step=0.01,
                format="%.2f",
                key="manual_amount"
            )
        with col2:
            tree_manual = load_category_tree()
            top_cats_manual = list(tree_manual.keys())
            manual_top = st.selectbox("Kategorie", options=top_cats_manual, key="manual_top")
            manual_subs = tree_manual.get(manual_top, {}).get("subcategories", ["Unbekannt"])
            manual_sub = st.selectbox("Unterkategorie", options=manual_subs, key="manual_sub")
            manual_note = st.text_input("Notiz (optional)", key="manual_note")

        submitted = st.form_submit_button("✅ Transaktion hinzufügen")

    if submitted:
        if not manual_store.strip():
            st.error("Bitte einen Store / eine Beschreibung eingeben.")
        else:
            from core.models import make_id
            new_transaction = {
                "store": manual_store.strip(),
                "amount": round(float(manual_amount), 2),
                "date": manual_date.strftime("%d.%m.%Y"),
                "top_category": manual_top,
                "sub_category": manual_sub,
                "category": None,
                "reference": f"MANUAL_{manual_date.strftime('%d%m%Y')}_{manual_store.strip()[:10]}",
                "note": manual_note.strip() if manual_note else ""
            }

            # Check for duplicates
            existing = load_transactions()
            existing_ids = {make_id(t) for t in existing}

            if make_id(new_transaction) in existing_ids:
                st.warning("⚠️ Diese Transaktion existiert bereits!")
            else:
                existing.append(new_transaction)
                save_transactions(existing)

                # Also save store to categories.json
                store_cats = load_store_categories()
                store_cats[manual_store.strip()] = {
                    "top": manual_top,
                    "sub": manual_sub
                }
                save_store_categories(store_cats)

                st.success(f"✅ Transaktion hinzugefügt: {manual_store} | {manual_amount:.2f}€ | {manual_date.strftime('%d.%m.%Y')}")
                st.rerun()

# ==========================================
# TAB 5 — EINSTELLUNGEN
# ==========================================
with tab5:
    st.subheader("⚙️ Einstellungen")

    tree = load_category_tree()
    store_categories = load_store_categories()

    # --- APP STATS ---
    st.markdown("### 📊 App-Statistiken")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Transaktionen gesamt", len(all_transactions))
    with col2:
        if df is not None:
            min_date = df["date"].min().strftime("%d.%m.%Y")
            max_date = df["date"].max().strftime("%d.%m.%Y")
            st.metric("📅 Zeitraum", f"{min_date} – {max_date}")
        else:
            st.metric("📅 Zeitraum", "—")
    with col3:
        if df is not None:
            num_months = df["date"].dt.to_period("M").nunique()
            st.metric("🗓️ Monate", num_months)
        else:
            st.metric("🗓️ Monate", "—")

    st.markdown("---")

    # --- RECATEGORIZATION ---
    st.markdown("### 🔄 Store neu kategorisieren")
    st.write("Ändere die Kategorie eines Stores — alle zugehörigen Transaktionen werden automatisch aktualisiert.")

    if store_categories:
        stores = sorted(store_categories.keys())
        selected_store = st.selectbox("Store auswählen", stores, key="recat_store")
        if selected_store:
            current = store_categories[selected_store]
            st.info(f"Aktuelle Kategorie: **{current['top']}** → **{current['sub']}**")
            top_categories = list(tree.keys())
            col1, col2 = st.columns(2)
            with col1:
                new_top = st.selectbox(
                    "Neue Kategorie", options=top_categories,
                    index=top_categories.index(current["top"]) if current["top"] in top_categories else 0,
                    key="recat_top"
                )
            with col2:
                subs = tree.get(new_top, {}).get("subcategories", ["Unbekannt"])
                current_sub_index = subs.index(current["sub"]) if current["sub"] in subs else 0
                new_sub = st.selectbox(
                    "Neue Unterkategorie", options=subs,
                    index=current_sub_index, key="recat_sub"
                )
            if st.button(f"✅ '{selected_store}' neu kategorisieren"):
                for t in all_transactions:
                    if t["store"] == selected_store:
                        t["top_category"] = new_top
                        t["sub_category"] = new_sub
                store_categories[selected_store] = {"top": new_top, "sub": new_sub}
                save_transactions(all_transactions)
                save_store_categories(store_categories)
                st.success(f"'{selected_store}' → {new_top} / {new_sub} — alle Transaktionen aktualisiert!")
                st.rerun()
    else:
        st.info("Noch keine kategorisierten Stores in diesem Profil.")

    st.markdown("---")

    st.markdown("---")

    # --- ERSTATTUNGSREGELN ---
    st.markdown("### 💸 Wiederkehrende Erstattungsregeln")
    st.write("Definiere wiederkehrende Erstattungen — sie werden automatisch auf alle passenden Transaktionen angewendet.")

    from core.reimbursement_manager import (
        load_reimbursement_rules, add_reimbursement_rule,
        delete_reimbursement_rule, toggle_reimbursement_rule,
        apply_reimbursement_rules
    )

    reimb_rules = load_reimbursement_rules()

    # Display existing rules
    if reimb_rules:
        st.markdown("#### Aktuelle Regeln")
        for rule in reimb_rules:
            status = "✅ Aktiv" if rule["active"] else "⏸️ Pausiert"
            total = sum(d["amount"] for d in rule["deductions"])
            with st.expander(f"💸 {rule['income_store']} — {status} — {total:.2f}€ gesamt"):
                for d in rule["deductions"]:
                    st.write(f"  • {d['sub_category']}: {d['amount']:.2f}€")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(
                        "⏸️ Pausieren" if rule["active"] else "▶️ Aktivieren",
                        key=f"rtoggle_{rule['income_store']}"
                    ):
                        toggle_reimbursement_rule(rule["income_store"])
                        apply_reimbursement_rules()
                        st.success("Regel aktualisiert und neu angewendet!")
                        st.rerun()
                with col2:
                    if st.button("🔄 Neu anwenden", key=f"reapply_{rule['income_store']}"):
                        apply_reimbursement_rules()
                        st.success("Regeln neu angewendet!")
                        st.rerun()
                with col3:
                    if st.button("🗑️ Löschen", key=f"rdelete_{rule['income_store']}"):
                        delete_reimbursement_rule(rule["income_store"])
                        apply_reimbursement_rules()
                        st.success(f"Regel für '{rule['income_store']}' gelöscht.")
                        st.rerun()
    else:
        st.info("Noch keine Erstattungsregeln definiert.")

    # Manual reapply button
    if reimb_rules:
        st.markdown("---")
        if st.button("🔄 Alle Regeln neu anwenden", type="secondary"):
            apply_reimbursement_rules()
            st.success("Alle Regeln neu angewendet!")
            st.rerun()

    st.markdown("---")
    st.markdown("#### ➕ Neue Erstattungsregel")

    # Get all Einnahmen stores
    einnahmen_stores = sorted(list(set(
        t["store"] for t in all_transactions
        if t.get("top_category") == "Einnahmen"
    ))) if all_transactions else []

    rule_store = st.selectbox(
        "Erstattung von Store",
        options=einnahmen_stores if einnahmen_stores else ["—"],
        key="rule_store"
    )

    # Show latest amount
    latest = 0.0
    if rule_store and rule_store != "—":
        from core.erstattung_manager import get_latest_erstattung_amount
        latest = get_latest_erstattung_amount(rule_store, all_transactions)
        st.info(f"💰 Letzter Betrag von **{rule_store}**: {latest:.2f}€")

    st.markdown("**Abzüge definieren** (welche Ausgaben werden erstattet?):")

    if "reimb_rows" not in st.session_state:
        st.session_state.reimb_rows = 1

    all_subcategories = sorted(list(set(
        sub for data in tree.values() for sub in data["subcategories"]
    )))

    new_deductions = []
    total_deducted = 0.0

    for i in range(st.session_state.reimb_rows):
        st.markdown(f"**Abzug {i+1}**")
        col1, col2 = st.columns(2)
        with col1:
            sub = st.selectbox(
                "Unterkategorie der Ausgabe",
                options=all_subcategories,
                key=f"reimb_sub_{i}"
            )
        with col2:
            amt = st.number_input(
                "Betrag (€)",
                min_value=0.01,
                value=100.0,
                step=10.0,
                key=f"reimb_amt_{i}"
            )
        new_deductions.append({"sub_category": sub, "amount": amt})
        total_deducted += amt

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Weiterer Abzug", key="add_reimb_row"):
            st.session_state.reimb_rows += 1
            st.rerun()
    with col2:
        if st.session_state.reimb_rows > 1:
            if st.button("➖ Entfernen", key="remove_reimb_row"):
                st.session_state.reimb_rows -= 1
                st.rerun()

    # Preview
    if latest > 0:
        remaining = round(latest - total_deducted, 2)
        if remaining >= 0:
            st.success(f"✅ Nach Abzügen verbleiben: **{remaining:.2f}€** der Erstattung")
        else:
            st.error(f"⚠️ Abzüge übersteigen Erstattung um {abs(remaining):.2f}€!")

    if st.button("💾 Regel speichern & anwenden", type="primary", key="save_reimb_rule"):
        if rule_store and rule_store != "—":
            add_reimbursement_rule(rule_store, new_deductions)
            apply_reimbursement_rules()
            st.session_state.reimb_rows = 1
            st.success(f"Regel für '{rule_store}' gespeichert und angewendet!")
            st.rerun()
        else:
            st.error("Bitte einen Store auswählen.")

    st.markdown("---")

    # --- CATEGORY TREE MANAGEMENT ---
    st.markdown("### 🌳 Kategorie-Baum verwalten")
    st.caption("Der Kategorie-Baum ist global und gilt für alle Profile.")

    for top, data in tree.items():
        with st.expander(f"📁 {top}"):
            for sub in data["subcategories"]:
                st.write(f"  • {sub}")

    st.markdown("---")

    st.markdown("#### ➕ Neue Unterkategorie hinzufügen")
    col1, col2, col3 = st.columns(3)
    with col1:
        existing_top = st.selectbox(
            "Zu welcher Kategorie?", options=list(tree.keys()), key="add_sub_top"
        )
    with col2:
        new_sub_name = st.text_input("Name der Unterkategorie", key="new_sub_name")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Unterkategorie hinzufügen"):
            if new_sub_name.strip():
                add_subcategory(existing_top, new_sub_name.strip())
                st.success(f"'{new_sub_name}' zu '{existing_top}' hinzugefügt!")
                st.rerun()
            else:
                st.error("Bitte einen Namen eingeben.")

    st.markdown("---")

    st.markdown("#### ➕ Neue Hauptkategorie hinzufügen")
    col1, col2 = st.columns(2)
    with col1:
        new_top_name = st.text_input("Name der Hauptkategorie", key="new_top_name")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Hauptkategorie hinzufügen"):
            if new_top_name.strip():
                add_top_category(new_top_name.strip())
                st.success(f"Hauptkategorie '{new_top_name}' hinzugefügt!")
                st.rerun()
            else:
                st.error("Bitte einen Namen eingeben.")