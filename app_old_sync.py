import streamlit as st
import os
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

# --- Load environment variables (.env) ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
COOKIE_PASSWORD = os.getenv("COOKIE_PASSWORD")

# --- Initialize cookie manager ---
cookies = EncryptedCookieManager(prefix="myapp_", password=COOKIE_PASSWORD)
if not cookies.ready():
    st.stop()

# --- Authentication token helpers ---
def save_token(token: str):
    cookies["sb_token"] = token
    cookies.save()

def get_token():
    return cookies.get("sb_token", "")

def clear_token():
    cookies["sb_token"] = ""
    cookies.save()

# --- Supabase client (basic, not cached since new instance is fast) ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def login_user(email: str, password: str):
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

def signup_user(email: str, password: str):
    # Supabase expects a dict for user credentials
    return supabase.auth.sign_up({"email": email, "password": password})

# --- CRUD Ops ---
@st.cache_data(ttl=5, show_spinner=False)
def get_tasks():
    response = supabase.table("tasks").select("*").execute()
    return getattr(response, "data", [])

def add_task(title: str, description: str):
    supabase.table("tasks").insert({"title": title, "description": description}).execute()
    get_tasks.clear()

def edit_task(task_id: int, update_fields: dict):
    supabase.table("tasks").update(update_fields).eq("id", task_id).execute()
    get_tasks.clear()

def delete_task(task_id: int):
    supabase.table("tasks").delete().eq("id", task_id).execute()
    get_tasks.clear()

# --- Streamlit UI ---
st.set_page_config(page_title="Supabase Task Manager", layout="wide")

def show_main_app():
    st.title("Task Manager with Supabase")
    st.sidebar.header("Manage Tasks")
    st.sidebar.write("You are logged in.")

    # --- Logout ---
    st.sidebar.header("Account")
    if st.sidebar.button("Logout"):
        clear_token()
        st.success("Logged out!")
        st.rerun()

    # --- Show current tasks ---
    tasks = get_tasks()
    st.subheader("Current Tasks")
    if tasks:
        for task in tasks:
            st.markdown(f"**ID:** {task['id']}")
            st.markdown(f"**Title:** {task['title']}")
            st.markdown(f"**Description:** {task.get('description', '')}")
            st.markdown("---")
    else:
        st.info("No tasks found.")

    # --- Add Task ---
    with st.sidebar.expander("Add Task"):
        add_title = st.text_input("Task Title", key="add_title")
        add_description = st.text_area("Task Description", key="add_desc")
        if st.button("Add Task"):
            if add_title.strip():
                add_task(add_title.strip(), add_description.strip())
                st.success("Task added!")
                st.rerun()
            else:
                st.warning("Please enter a task title.")

    # --- Edit Task ---
    with st.sidebar.expander("Edit Task"):
        if tasks:
            task_options = [(t["id"], t["title"]) for t in tasks]
            task_to_edit = st.selectbox(
                "Select Task to Edit",
                options=task_options,
                format_func=lambda x: f"ID:{x[0]} - {x[1]}",
                key="edit_select"
            )
            new_title = st.text_input("New Title", value="", key="edit_title")
            new_description = st.text_area("New Description", value="", key="edit_desc")
            if st.button("Update Task"):
                task_id = task_to_edit[0]
                update_fields = {}
                if new_title.strip():
                    update_fields["title"] = new_title.strip()
                if new_description.strip():
                    update_fields["description"] = new_description.strip()
                if update_fields:
                    edit_task(task_id, update_fields)
                    st.success("Task updated!")
                    st.rerun()
                else:
                    st.warning("Please enter new title or description to update.")
        else:
            st.info("No tasks to edit.")

    # --- Delete Task ---
    with st.sidebar.expander("Delete Task"):
        if tasks:
            task_options = [(t["id"], t["title"]) for t in tasks]
            task_to_delete = st.selectbox(
                "Select Task to Delete",
                options=task_options,
                format_func=lambda x: f"ID:{x[0]} - {x[1]}",
                key="delete_select"
            )
            if st.button("Delete Task"):
                delete_task(task_to_delete[0])
                st.success("Task deleted!")
                st.rerun()
        else:
            st.info("No tasks to delete.")

# --- Login/Signup logic ---
token = get_token()
if not token:
    st.title("🔒 Authentication")
    mode = st.radio("Choose an option", ("Sign In", "Sign Up"))
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if mode == "Sign In":
        if st.button("Sign In"):
            try:
                auth_res = login_user(email, password)
                session = getattr(auth_res, "session", None)
                if session and session.access_token:
                    save_token(session.access_token)
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error("Login failed. Check your credentials.")
            except Exception as e:
                st.error(f"Login failed: {e}")
        st.stop()

    elif mode == "Sign Up":
        if st.button("Sign Up"):
            try:
                res = signup_user(email, password)
                if getattr(res, "user", None):
                    st.success("Registration successful! Please check your email for a verification link before logging in.")
                    st.info("After verifying your email, please return to the Sign In page to login.")
                    # Rerun the app to return user to Sign In
                    st.rerun()
                else:
                    st.error("Sign up failed. Please try again.")
            except Exception as e:
                st.error(f"Sign-up failed: {e}")
        st.stop()
else:
    show_main_app()
