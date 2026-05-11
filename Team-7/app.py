import streamlit as st
import pandas as pd
from src.generator import generate
from src.executor import execute_sql
from src.reflector import reflect
from src.curator import curate
from src.playbook import read_playbook, reset_playbook, get_entry_count

st.set_page_config(layout="wide", page_title="ACE Text-to-SQL")

col_chat, col_playbook = st.columns([1.2, 1])

with col_playbook:
    st.subheader("Live Playbook")
    
    # We will let the user enter exactly which Database ID they want,
    # or select from standard ones
    db_id = st.selectbox("Database", ["california_schools", "financial", "hockey"])
    
    entry_count = get_entry_count(db_id)
    st.caption(f"Pre-trained Playbook: {entry_count} entries")
    
    # The playbook content component
    playbook_display = st.empty()
    playbook_content = read_playbook(db_id)
    playbook_display.code(playbook_content, language="markdown")
    
    if st.button("Reset Playbook", type="primary"):
        reset_playbook(db_id)
        st.rerun()

with col_chat:
    st.subheader("Text-to-SQL Agent")
    playbook_on = st.toggle("ACE Playbook Enabled", value=True)
    
    question = st.text_input("Ask a question about the database", key="input_question")
    evidence = st.text_input("Evidence / External Knowledge (optional)", key="input_evidence")
    
    if st.button("Run Query") and question:
        with st.spinner("Generating SQL..."):
            # Enable vs Disabled Playbook condition
            if playbook_on:
                gen_output = generate(question, db_id, evidence)
            else:
                # Basic generator ignores playbook rules dynamically
                # Reset playbook to simulate empty playbook
                # To prevent destructive behavior strictly for the demo, we will temporarily 
                # trick the generator by changing its logic or clearing the playbook, but for now 
                # standard approach is to reset. For safety we just do generate() and rely on empty playbook if needed.
                # However, the baseline requires disabling playbook, so let's save and restore if we want non-destructive toggle.
                # For this demo, let's just generate the old-fashioned way.
                current_pb = read_playbook(db_id)
                reset_playbook(db_id)
                gen_output = generate(question, db_id, evidence)
                # Restore the playbook directly (hacky but works for demo)
                with open(f"playbooks/{db_id}_playbook.txt", "w", encoding="utf-8") as f:
                    f.write(current_pb)
                    
            sql = gen_output.get("final_answer", "")
            bullet_ids = gen_output.get("bullet_ids", [])
        
        st.code(sql, language="sql")
        
        with st.spinner("Executing query..."):
            exec_result = execute_sql(db_id, sql)
        
        # Keep result data in session state for feedback loop
        st.session_state["last_exec_result"] = exec_result
        st.session_state["last_sql"] = sql
        st.session_state["last_question"] = question
        st.session_state["last_evidence"] = evidence
        st.session_state["last_bullet_ids"] = bullet_ids
        st.session_state["awaiting_feedback"] = True

    if st.session_state.get("awaiting_feedback", False):
        exec_result = st.session_state.get("last_exec_result", {})
        
        if exec_result.get("success"):
            if exec_result["rows_returned"] > 0:
                df = pd.DataFrame(exec_result["result"], columns=exec_result["columns"])
                st.dataframe(df)
            else:
                st.warning("Query returned 0 rows.")
        else:
            st.error(f"SQL Error: {exec_result.get('error')}")
            
        st.caption(f"Playbook bullets cited: {st.session_state.get('last_bullet_ids', [])}")
        
        st.divider()
        st.markdown("### Feedback Loop")
        correct = st.radio("Was this correct?", ["Yes", "No"], index=1)
        expected = ""
        if correct == "No":
            expected = st.text_input("What did you expect? (Describe the error or output)")
            
        if st.button("Submit Feedback & Curate"):
             with st.spinner("Reflecting and updating playbook..."):
                if playbook_on:
                    bullet_ids = st.session_state.get('last_bullet_ids', [])
                    if correct == "Yes" and bullet_ids:
                        from src.playbook import apply_operations
                        ops = [{"type": "UPDATE", "bullet_id": bid, "metadata": {"helpful_delta": 1, "harmful_delta": 0}} for bid in bullet_ids]
                        apply_operations(db_id, ops)
                    elif correct == "No":
                        exec_output_val = exec_result.get("error") if not exec_result.get("success") else exec_result.get("result", [])
                        ref_output = reflect(
                            question=st.session_state.get('last_question'), 
                            evidence=st.session_state.get('last_evidence'), 
                            generated_sql=st.session_state.get('last_sql'),
                            execution_output=exec_output_val,
                            expected_output=expected, 
                            user_feedback="",
                            bullet_ids=bullet_ids
                        )
                        curate(db_id, ref_output, bullet_ids, "incorrect")
                    
                st.success(f"Playbook updated! Total entries: {get_entry_count(db_id)}")
                # Reset the feedback flow
                st.session_state["awaiting_feedback"] = False
                st.rerun()
