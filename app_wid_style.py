import streamlit as st
import os
import asyncio
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager
import nest_asyncio

nest_asyncio.apply()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
COOKIE_PASSWORD = os.getenv("COOKIE_PASSWORD")

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
cookies = EncryptedCookieManager(prefix="femtotech_", password=COOKIE_PASSWORD)
if not cookies.ready():
    st.stop()

# --- Token helpers ---
def save_token(token: str):
    cookies["sb_token"] = token
    cookies.save()

def get_token():
    return cookies.get("sb_token", "")

def clear_token():
    cookies["sb_token"] = ""
    cookies.save()

# --- Supabase client ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Async backend functions ---
async def login_user_async(email: str, password: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: supabase.auth.sign_in_with_password({"email": email, "password": password}),
    )


async def signup_user_async(email: str, password: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: supabase.auth.sign_up({"email": email, "password": password}),
    )


async def get_tasks_async():
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: supabase.table("tasks").select("*").execute(),
    )
    return getattr(response, "data", [])


async def add_task_async(title: str, description: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: supabase.table("tasks").insert({"title": title, "description": description}).execute(),
    )


async def edit_task_async(task_id: int, update_fields: dict):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: supabase.table("tasks").update(update_fields).eq("id", task_id).execute(),
    )


async def delete_task_async(task_id: int):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: supabase.table("tasks").delete().eq("id", task_id).execute(),
    )


# --- Async helper ---
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

# --- Custom CSS Styling ---
st.markdown(
    """
    <style>
    /* GENERAL */
    .stApp {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #e0f7fa 0%, #80deea 100%);
        color: #0a3d62;
    }
    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background-color: #073b4c;
        color: white;
        font-weight: 600;
    }
    [data-testid="stSidebar"] .css-1d391kg {
        padding-top: 1rem;
    }

    /* HEADERS */
    h1, h2, h3, h4 {
        font-weight: 700;
        color: #074047;
    }

    /* BUTTONS */
    div.stButton > button:first-child {
        background-color: #118ab2;
        color: white;
        border-radius: 8px;
        padding: 0.5em 1.2em;
        transition: background-color 0.2s ease;
        font-weight: 600;
    }
    div.stButton > button:first-child:hover {
        background-color: #06aed5;
        color: white;
    }

    /* TEXT INPUTS */
    .stTextInput>div>div>input, .stTextArea>div>textarea {
        border-radius: 8px;
        border: 1.8px solid #118ab2;
        padding: 0.4em 0.6em;
    }
    .stTextInput>div>label, .stTextArea>div>label {
        font-weight: 600;
        color: #073b4c;
    }

    /* Cards for tasks */
    .task-card {
        background-color: white;
        padding: 1rem;
        margin-bottom: 0.8rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgb(0 0 0 / 0.1);
        transition: box-shadow 0.2s ease;
    }
    .task-card:hover {
        box-shadow: 0 8px 12px rgb(0 0 0 / 0.2);
    }

    /* Badge */
    .task-badge {
        background-color: #06aed5;
        color: white;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 10px;
        font-size: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

async def show_main_app_async():
    st.sidebar.header("👾 Femtotech Blogs Manager")
    st.sidebar.markdown("Built with :blue[Supabase] and :orange[Streamlit]")

    # Get user token info display (optional)
    token = get_token()
    if token:
        st.sidebar.success("✅ Logged in")
        if st.sidebar.button("🚪 Logout", key="logout_btn"):
            clear_token()
            st.rerun()
    else:
        st.sidebar.warning("🔒 Not logged in")

    # Top header and description
    st.markdown("<h1 style='text-align:center;'>⚡ Femtotech Blogs Task Manager</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center;  font-size:1rem; color:#074047;'>"
        "Manage your blog posts, drafts, and ideas efficiently using this simple, modern app.</p>",
        unsafe_allow_html=True,
    )

    tasks = await get_tasks_async()

    # Search/filter tasks by title
    search_term = st.text_input("🔎 Search Tasks by Title", value="", placeholder="Search for a blog by title...")
    filtered_tasks = [t for t in tasks if search_term.lower() in t["title"].lower()] if search_term else tasks

    st.subheader(f"📝 Blog Posts ({len(filtered_tasks)})")

    if filtered_tasks:
        # Show tasks in cards grouped in 2-columns
        for i in range(0, len(filtered_tasks), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                if i + j >= len(filtered_tasks):
                    break
                task = filtered_tasks[i + j]
                with col:
                    st.markdown(
                        f"""
                        <div class="task-card">
                            <h4>{task['title']} <span class="task-badge">ID:{task['id']}</span></h4>
                            <p style="color:#555;">{task.get("description", "(No Description)")}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    # Quick delete button next to each card
                    if st.button(f"🗑️ Delete", key=f"quick_del_{task['id']}", help="Delete this blog post"):
                        with st.spinner("Deleting blog post..."):
                            await delete_task_async(task['id'])
                        st.success("Deleted blog post!")
                        st.rerun()
    else:
        st.info("No blog posts found that match your search.")

    # Sidebar Expanders for CRUD operations
    with st.sidebar.expander("➕ Add New Blog Post"):
        new_title = st.text_input("Title of the Blog", key="add_title_ui")
        new_desc = st.text_area("Content/Draft", key="add_desc_ui")
        if st.button("Add Blog Post"):
            if new_title.strip():
                with st.spinner("Adding blog post..."):
                    await add_task_async(new_title.strip(), new_desc.strip())
                st.success("Blog post added successfully!")
                st.rerun()
            else:
                st.warning("Title cannot be empty.")

    with st.sidebar.expander("✏️ Edit Existing Blog"):
        if tasks:
            task_options = [(t["id"], t["title"]) for t in tasks]
            task_to_edit = st.selectbox("Select Blog to Edit", options=task_options, format_func=lambda x: f"ID:{x[0]} - {x[1]}", key="edit_task_select")
            edit_title = st.text_input("New Title (leave blank to keep unchanged)", key="edit_title_ui")
            edit_desc = st.text_area("New Content/Draft (leave blank to keep unchanged)", key="edit_desc_ui")

            if st.button("Update Blog Post"):
                update_fields = {}
                if edit_title.strip():
                    update_fields["title"] = edit_title.strip()
                if edit_desc.strip():
                    update_fields["description"] = edit_desc.strip()
                if update_fields:
                    with st.spinner("Updating blog post..."):
                        await edit_task_async(task_to_edit[0], update_fields)
                    st.success("Blog post updated!")
                    st.rerun()
                else:
                    st.warning("Please enter new title or content to update.")
        else:
            st.info("No blog posts available to edit.")

    with st.sidebar.expander("🗑️ Delete Blog Post"):
        if tasks:
            task_options = [(t["id"], t["title"]) for t in tasks]
            task_to_delete = st.selectbox("Select Blog to Delete", options=task_options, format_func=lambda x: f"ID:{x[0]} - {x[1]}", key="delete_task_select")
            if st.button("Delete Selected Blog"):
                with st.spinner("Deleting selected blog..."):
                    await delete_task_async(task_to_delete[0])
                st.success("Deleted blog post!")
                st.rerun()
        else:
            st.info("No blog posts available to delete.")

    # Bulk operations
    with st.sidebar.expander("🔄 Bulk Operations"):
        if tasks:
            selected = st.multiselect(
                "Select blog posts to delete",
                options=[(task["id"], task["title"]) for task in tasks],
                format_func=lambda x: f"ID:{x[0]} - {x[1]}",
                key="bulk_delete_select_ui"
            )
            if st.button("Delete Selected"):
                if selected:
                    with st.spinner(f"Deleting {len(selected)} blog posts..."):
                        await asyncio.gather(*[delete_task_async(task[0]) for task in selected])
                    st.success(f"Deleted {len(selected)} blog posts!")
                    st.rerun()
                else:
                    st.warning("Please select at least one blog post.")
        else:
            st.info("No blog posts available for bulk operations.")

async def handle_auth_async():
    token = get_token()
    if not token:
        st.title("🔒 Femtotech Blogs - Authentication")
        mode = st.radio("Choose Action", ("Sign In", "Sign Up"))
        email = st.text_input("Email Address")
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
                            st.error("Failed to login. Please check credentials.")
                except Exception as e:
                    st.error(f"Sign in error: {e}")
                    st.stop()
        else:
            if st.button("Sign Up"):
                try:
                    with st.spinner("Creating your account..."):
                        res = await signup_user_async(email, password)
                        if getattr(res, "user", None):
                            st.success("Registration successful! Check your email for verification link.")
                            st.info("After verification, return to Sign In.")
                            st.rerun()
                        else:
                            st.error("Sign up failed. Try again.")
                except Exception as e:
                    st.error(f"Sign up error: {e}")
                    st.stop()
    else:
        await show_main_app_async()

def main():
    run_async(handle_auth_async())

if __name__ == "__main__":
    main()
