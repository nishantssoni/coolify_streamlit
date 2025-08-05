import streamlit as st
import os
import asyncio
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager
import nest_asyncio

# Apply nest_asyncio to handle async in Streamlit
nest_asyncio.apply()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
COOKIE_PASSWORD = os.getenv("COOKIE_PASSWORD")

# Validate environment variables
if not SUPABASE_URL:
    st.error("SUPABASE_URL environment variable is not set. Please check your .env file.")
    st.stop()

if not SUPABASE_KEY:
    st.error("SUPABASE_KEY environment variable is not set. Please check your .env file.")
    st.stop()

if not COOKIE_PASSWORD:
    st.error("COOKIE_PASSWORD environment variable is not set. Please check your .env file.")
    st.stop()

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

# --- Supabase client (same pattern as your working code) ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Async Authentication Functions ---
async def login_user_async(email: str, password: str):
    """Async login function"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        lambda: supabase.auth.sign_in_with_password({"email": email, "password": password})
    )

async def signup_user_async(email: str, password: str):
    """Async signup function"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: supabase.auth.sign_up({"email": email, "password": password})
    )

# --- Async CRUD Operations (following your working pattern) ---
async def get_tasks_async():
    """Async function to get all tasks"""
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: supabase.table("tasks").select("*").execute()
    )
    return getattr(response, "data", [])

async def add_task_async(title: str, description: str):
    """Async function to add a new task"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: supabase.table("tasks").insert({"title": title, "description": description}).execute()
    )

async def edit_task_async(task_id: int, update_fields: dict):
    """Async function to edit a task"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: supabase.table("tasks").update(update_fields).eq("id", task_id).execute()
    )

async def delete_task_async(task_id: int):
    """Async function to delete a task"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: supabase.table("tasks").delete().eq("id", task_id).execute()
    )

# --- Async wrapper for Streamlit ---
def run_async(coro):
    """Helper function to run async functions in Streamlit"""
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

# --- Streamlit UI ---
st.set_page_config(page_title="⚡ Async Supabase Task Manager", layout="wide")

async def show_main_app_async():
    st.title("⚡ Async Task Manager with Supabase")
    st.sidebar.header("Manage Tasks")
    st.sidebar.write("You are logged in.")

    # --- Logout ---
    st.sidebar.header("Account")
    if st.sidebar.button("Logout"):
        clear_token()
        st.success("Logged out!")
        st.rerun()

    # --- Show current tasks with loading spinner ---
    with st.spinner("Loading tasks..."):
        tasks = await get_tasks_async()
    
    st.subheader("Current Tasks")
    if tasks:
        for task in tasks:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**ID:** {task['id']}")
                st.markdown(f"**Title:** {task['title']}")
                st.markdown(f"**Description:** {task.get('description', '')}")
            with col2:
                # Quick delete button for each task
                if st.button(f"🗑️", key=f"quick_delete_{task['id']}", help="Delete this task"):
                    with st.spinner("Deleting task..."):
                        await delete_task_async(task['id'])
                    st.success("Task deleted!")
                    st.rerun()
            st.markdown("---")
    else:
        st.info("No tasks found.")

    # --- Add Task ---
    with st.sidebar.expander("➕ Add Task"):
        add_title = st.text_input("Task Title", key="add_title")
        add_description = st.text_area("Task Description", key="add_desc")
        if st.button("Add Task"):
            if add_title.strip():
                with st.spinner("Adding task..."):
                    await add_task_async(add_title.strip(), add_description.strip())
                st.success("Task added!")
                st.rerun()
            else:
                st.warning("Please enter a task title.")

    # --- Edit Task ---
    with st.sidebar.expander("✏️ Edit Task"):
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
                    with st.spinner("Updating task..."):
                        await edit_task_async(task_id, update_fields)
                    st.success("Task updated!")
                    st.rerun()
                else:
                    st.warning("Please enter new title or description to update.")
        else:
            st.info("No tasks to edit.")

    # --- Delete Task ---
    with st.sidebar.expander("🗑️ Delete Task"):
        if tasks:
            task_options = [(t["id"], t["title"]) for t in tasks]
            task_to_delete = st.selectbox(
                "Select Task to Delete",
                options=task_options,
                format_func=lambda x: f"ID:{x[0]} - {x[1]}",
                key="delete_select"
            )
            if st.button("Delete Task"):
                with st.spinner("Deleting task..."):
                    await delete_task_async(task_to_delete[0])
                st.success("Task deleted!")
                st.rerun()
        else:
            st.info("No tasks to delete.")

    # --- Bulk Operations ---
    with st.sidebar.expander("🔄 Bulk Operations"):
        if tasks:
            st.subheader("Bulk Delete")
            selected_tasks = st.multiselect(
                "Select tasks to delete",
                options=[(t["id"], t["title"]) for t in tasks],
                format_func=lambda x: f"ID:{x[0]} - {x[1]}",
                key="bulk_delete_select"
            )
            if st.button("Delete Selected Tasks") and selected_tasks:
                with st.spinner(f"Deleting {len(selected_tasks)} tasks..."):
                    # Run deletions concurrently for better performance
                    delete_tasks = [delete_task_async(task[0]) for task in selected_tasks]
                    await asyncio.gather(*delete_tasks)
                st.success(f"Deleted {len(selected_tasks)} tasks!")
                st.rerun()
        else:
            st.info("No tasks available for bulk operations.")

# --- Async Login/Signup logic (following your working pattern) ---
async def handle_auth_async():
    token = get_token()
    if not token:
        st.title("🔒 Authentication")
        mode = st.radio("Choose an option", ("Sign In", "Sign Up"))
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if mode == "Sign In":
            if st.button("Sign In"):
                try:
                    with st.spinner("Signing in..."):
                        auth_res = await login_user_async(email, password)
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
                    with st.spinner("Creating account..."):
                        res = await signup_user_async(email, password)
                    if getattr(res, "user", None):
                        st.success("Registration successful! Please check your email for a verification link before logging in.")
                        st.info("After verifying your email, please return to the Sign In page to login.")
                        st.rerun()
                    else:
                        st.error("Sign up failed. Please try again.")
                except Exception as e:
                    st.error(f"Sign-up failed: {e}")
            st.stop()
    else:
        await show_main_app_async()

# --- Main execution ---
def main():
    """Main function that runs the async app"""
    run_async(handle_auth_async())

if __name__ == "__main__":
    main()