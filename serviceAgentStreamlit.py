import streamlit as st
import requests
import uuid
import json
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Configure Streamlit page
st.set_page_config(
    page_title="Document AI Service Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "namespace" not in st.session_state:
    st.session_state.namespace = "default"
if "page" not in st.session_state:
    st.session_state.page = "chat"

# Sidebar Navigation
with st.sidebar:
    st.title("🤖 AI Service Agent")
    
    # Navigation
    page = st.radio(
        "📍 الانتقال",
        ["💬 المحادثة", "📋 تتبع الطلبات", "📊 الإحصائيات", "⚙️ الإعدادات"],
        key="navigation"
    )
    
    # Map page names
    page_mapping = {
        "💬 المحادثة": "chat",
        "📋 تتبع الطلبات": "requests",
        "📊 الإحصائيات": "stats",
        "⚙️ الإعدادات": "settings"
    }
    st.session_state.page = page_mapping[page]
    
    st.divider()
    
    # API Status
    st.subheader("🔗 حالة الاتصال")
    try:
        response = requests.get(f"{API_BASE_URL}/namespaces", timeout=2)
        if response.status_code == 200:
            st.success("✅ متصل")
        else:
            st.error("❌ خطأ في الاتصال")
    except:
        st.error("❌ غير متصل")
        st.warning("تأكد من تشغيل الخادم على المنفذ 8000")

# Helper functions
def get_requests_data(page=1, limit=10, status=None, service_name=None):
    """Get requests data from API"""
    try:
        params = {"page": page, "limit": limit}
        if status:
            params["status"] = status
        if service_name:
            params["service_name"] = service_name
            
        response = requests.get(f"{API_BASE_URL}/requests", params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"خطأ في جلب البيانات: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"خطأ: {str(e)}")
        return None

def get_request_details(request_id):
    """Get specific request details"""
    try:
        response = requests.get(f"{API_BASE_URL}/requests/{request_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"خطأ: {str(e)}")
        return None

def update_request_status(request_id, status, notes=None):
    """Update request status"""
    try:
        data = {"request_id": request_id, "status": status}
        if notes:
            data["notes"] = notes
            
        response = requests.put(f"{API_BASE_URL}/requests/{request_id}/status", json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        st.error(f"خطأ في التحديث: {str(e)}")
        return False

def get_stats():
    """Get statistics from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"خطأ: {str(e)}")
        return None

# Status color mapping
status_colors = {
    "pending": "🟡",
    "in_progress": "🔵", 
    "completed": "🟢",
    "rejected": "🔴",
    "cancelled": "⚫"
}

status_names = {
    "pending": "قيد الانتظار",
    "in_progress": "قيد المعالجة",
    "completed": "مكتمل",
    "rejected": "مرفوض", 
    "cancelled": "ملغي"
}

# Main Content based on selected page
if st.session_state.page == "chat":
    st.header("💬 المحادثة مع الوكيل الذكي")
    
    # Chat settings in columns
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Namespace selection
        namespaces = ["default"]
        try:
            response = requests.get(f"{API_BASE_URL}/namespaces", timeout=5)
            if response.status_code == 200:
                namespaces = response.json().get("namespaces", ["default"])
                if not namespaces:
                    namespaces = ["default"]
        except:
            pass
        
        selected_namespace = st.selectbox(
            "📁 اختيار مجموعة البيانات:", 
            options=namespaces, 
            index=0
        )
        st.session_state.namespace = selected_namespace
    
    with col2:
        if st.button("🔄 جلسة جديدة", type="secondary"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.success("تم بدء جلسة جديدة!")
            st.rerun()
    
    with col3:
        if st.button("🗑️ مسح المحادثة", type="secondary"):
            st.session_state.messages = []
            st.success("تم مسح المحادثة!")
            st.rerun()
    
    st.divider()
    
    # Display welcome message if no messages
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown("""
            ## 👋 مرحباً بك في الوكيل الذكي للخدمات
            
            **يمكنني مساعدتك في:**
            - 🔍 تحديد الخدمة المناسبة لطلبك
            - 📝 جمع المعلومات المطلوبة مع التحقق من صحتها
            - 📋 إرسال طلب الخدمة وتتبعه
            
            **أمثلة على الطلبات:**
            - "أريد تجديد الهوية الوطنية"
            - "أحتاج رخصة قيادة جديدة"
            - "كيف أحصل على جواز سفر؟"
            
            **✨ ابدأ بكتابة طلبك أدناه**
            """)
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Display service info if available
            if message.get("service_info"):
                with st.expander("📋 تفاصيل الخدمة"):
                    info = message["service_info"]
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**اسم الخدمة:**", info.get("service_name", "غير محدد"))
                        st.write("**مستوى الثقة:**", info.get("confidence", "غير محدد"))
                    with col2:
                        st.write("**المدة المتوقعة:**", info.get("estimated_processing_time", "غير محدد"))
                        st.write("**الحقول المطلوبة:**")
                        for field in info.get("required_fields", []):
                            st.write(f"• {field}")
    
    # Chat input
    if prompt := st.chat_input("اكتب رسالتك هنا..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response from agent
        with st.chat_message("assistant"):
            with st.spinner("جاري المعالجة..."):
                try:
                    chat_data = {
                        "session_id": st.session_state.session_id,
                        "message": prompt,
                        "namespace": st.session_state.namespace
                    }
                    
                    response = requests.post(f"{API_BASE_URL}/chat", json=chat_data, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        agent_response = result["response"]
                        
                        # Display agent response
                        st.markdown(agent_response)
                        
                        # Prepare message data for storage
                        message_data = {
                            "role": "assistant", 
                            "content": agent_response
                        }
                        
                        # Show validation error if any
                        if result.get("validation_error"):
                            st.error(f"خطأ في التحقق: {result['validation_error']}")
                        
                        # Show service info if available
                        if result.get("service_identified") and result.get("service_info"):
                            service_info = result["service_info"]
                            message_data["service_info"] = service_info
                            
                            with st.expander("📋 تفاصيل الخدمة"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write("**اسم الخدمة:**")
                                    st.code(service_info.get("service_name", "N/A"))
                                    st.write("**مستوى الثقة:**")
                                    confidence = service_info.get("confidence", "منخفض")
                                    if confidence == "عالي":
                                        st.success(confidence)
                                    elif confidence == "متوسط":
                                        st.warning(confidence)
                                    else:
                                        st.error(confidence)
                                
                                with col2:
                                    st.write("**المدة المتوقعة:**")
                                    st.info(service_info.get("estimated_processing_time", "غير محدد"))
                                    st.write("**الحقول المطلوبة:**")
                                    fields = service_info.get("required_fields", [])
                                    for field in fields:
                                        st.write(f"• {field}")
                        
                        # Show completion status
                        if result.get("completed"):
                            st.success("✅ تم إكمال طلب الخدمة بنجاح!")
                            st.balloons()
                        
                        # Add agent response to session
                        st.session_state.messages.append(message_data)
                        
                    else:
                        error_msg = f"❌ خطأ في الاتصال: {response.status_code}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                        
                except requests.exceptions.Timeout:
                    error_msg = "⏰ انتهت مهلة الاتصال. يرجى المحاولة مرة أخرى."
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                except requests.exceptions.ConnectionError:
                    error_msg = "🔌 لا يمكن الاتصال بالخادم. تأكد من تشغيل FastAPI."
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                except Exception as e:
                    error_msg = f"❌ خطأ غير متوقع: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

elif st.session_state.page == "requests":
    st.header("📋 تتبع وإدارة الطلبات")
    
    # Search and filter section
    with st.expander("🔍 البحث والتصفية", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_request_id = st.text_input("🔢 رقم الطلب", placeholder="أدخل رقم الطلب...")
        
        with col2:
            filter_status = st.selectbox(
                "📊 الحالة",
                ["الكل"] + list(status_names.values())
            )
        
        with col3:
            filter_service = st.text_input("🔍 اسم الخدمة", placeholder="البحث في اسم الخدمة...")
    
    # Search specific request
    if search_request_id:
        st.subheader("📄 تفاصيل الطلب")
        request_details = get_request_details(search_request_id)
        
        if request_details:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write("**رقم الطلب:**", request_details["request_id"])
                st.write("**الخدمة:**", request_details["service_name"])
                st.write("**الحالة:**", f"{status_colors.get(request_details['status'], '⚪')} {status_names.get(request_details['status'], request_details['status'])}")
                st.write("**تاريخ الإنشاء:**", request_details["created_at"][:19])
                st.write("**آخر تحديث:**", request_details["updated_at"][:19])
                
                if request_details.get("notes"):
                    st.write("**ملاحظات:**", request_details["notes"])
                
                # User data
                if request_details.get("user_data"):
                    st.write("**بيانات المستخدم:**")
                    for key, value in request_details["user_data"].items():
                        st.write(f"• **{key}:** {value}")
            
            with col2:
                st.subheader("تحديث الحالة")
                new_status = st.selectbox(
                    "اختر الحالة الجديدة:",
                    options=["pending", "in_progress", "completed", "rejected", "cancelled"],
                    format_func=lambda x: status_names.get(x, x),
                    index=["pending", "in_progress", "completed", "rejected", "cancelled"].index(request_details["status"])
                )
                
                notes = st.text_area("ملاحظات (اختيارية)", height=100)
                
                if st.button("💾 تحديث الحالة", type="primary"):
                    if update_request_status(search_request_id, new_status, notes):
                        st.success("✅ تم تحديث الحالة بنجاح!")
                        st.rerun()
                    else:
                        st.error("❌ فشل في تحديث الحالة")
        else:
            st.error("❌ لم يتم العثور على الطلب")
    
    st.divider()
    
    # All requests table
    st.subheader("📊 جميع الطلبات")
    
    # Prepare filters
    status_filter = None
    if filter_status != "الكل":
        status_filter = [k for k, v in status_names.items() if v == filter_status][0]
    
    service_filter = filter_service if filter_service else None
    
    # Pagination controls
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        page_size = st.selectbox("📄 عدد العناصر:", [10, 25, 50], index=0)
    
    # Get requests data
    requests_data = get_requests_data(
        page=1, 
        limit=page_size, 
        status=status_filter, 
        service_name=service_filter
    )
    
    if requests_data and requests_data["requests"]:
        # Display requests in a table
        df_data = []
        for req in requests_data["requests"]:
            df_data.append({
                "رقم الطلب": req["request_id"][:8] + "...",
                "الخدمة": req["service_name"],
                "الحالة": f"{status_colors.get(req['status'], '⚪')} {status_names.get(req['status'], req['status'])}",
                "تاريخ الإنشاء": req["created_at"][:19],
                "آخر تحديث": req["updated_at"][:19],
                "الجلسة": req["session_id"][:8] + "..." if req["session_id"] else "غير محدد"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Pagination info
        total_pages = requests_data.get("total_pages", 1)
        current_page = requests_data.get("page", 1)
        total_requests = requests_data.get("total", 0)
        
        st.info(f"📊 إجمالي الطلبات: {total_requests} | الصفحة: {current_page} من {total_pages}")
        
    else:
        st.info("📝 لا توجد طلبات متاحة")

elif st.session_state.page == "stats":
    st.header("📊 الإحصائيات والتقارير")
    
    # Get statistics
    stats_data = get_stats()
    
    if stats_data:
        # Summary cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📋 إجمالي الطلبات",
                stats_data["total_requests"],
                delta=None
            )
        
        with col2:
            st.metric(
                "🟡 قيد الانتظار",
                stats_data["pending_requests"],
                delta=None
            )
        
        with col3:
            st.metric(
                "🔵 قيد المعالجة", 
                stats_data["in_progress_requests"],
                delta=None
            )
        
        with col4:
            st.metric(
                "🟢 مكتملة",
                stats_data["completed_requests"],
                delta=None
            )
        
        st.divider()
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Status distribution pie chart
            status_data = [
                stats_data["pending_requests"],
                stats_data["in_progress_requests"], 
                stats_data["completed_requests"]
            ]
            status_labels = ["قيد الانتظار", "قيد المعالجة", "مكتملة"]
            
            fig_pie = px.pie(
                values=status_data,
                names=status_labels,
                title="📊 توزيع الطلبات حسب الحالة"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Service distribution bar chart
            if stats_data["service_distribution"]:
                services = [item["service_name"] for item in stats_data["service_distribution"]]
                counts = [item["count"] for item in stats_data["service_distribution"]]
                
                fig_bar = px.bar(
                    x=services,
                    y=counts,
                    title="📈 توزيع الطلبات حسب نوع الخدمة"
                )
                fig_bar.update_xaxes(title="نوع الخدمة")
                fig_bar.update_yaxes(title="عدد الطلبات")
                st.plotly_chart(fig_bar, use_container_width=True)
    
    else:
        st.error("❌ لا يمكن جلب الإحصائيات")

elif st.session_state.page == "settings":
    st.header("⚙️ الإعدادات")
    
    # File upload section
    st.subheader("📁 رفع المستندات")
    st.markdown("رفع مستندات الخدمات (TXT/PDF) لتدريب الوكيل الذكي")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Namespace selection for upload
        namespaces = ["default"]
        try:
            response = requests.get(f"{API_BASE_URL}/namespaces", timeout=5)
            if response.status_code == 200:
                namespaces = response.json().get("namespaces", ["default"])
                if not namespaces:
                    namespaces = ["default"]
        except:
            pass
        
        upload_namespace = st.selectbox(
            "اختر مجموعة البيانات:", 
            options=namespaces + ["إنشاء مجموعة جديدة"], 
            index=0
        )
        
        if upload_namespace == "إنشاء مجموعة جديدة":
            upload_namespace = st.text_input("اسم المجموعة الجديدة:", placeholder="أدخل اسم المجموعة...")
    
    with col2:
        uploaded_file = st.file_uploader(
            "اختر ملف:",
            type=['txt', 'pdf'],
            help="رفع مستندات تحتوي على معلومات الخدمات"
        )
    
    if uploaded_file is not None and upload_namespace:
        if st.button("📤 رفع الملف", type="primary"):
            try:
                with st.spinner("جاري رفع الملف..."):
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    data = {"namespace": upload_namespace}
                    response = requests.post(f"{API_BASE_URL}/upload", files=files, data=data, timeout=30)
                    
                    if response.status_code == 200:
                        st.success(f"✅ تم رفع الملف بنجاح إلى '{upload_namespace}'!")
                        st.balloons()
                    else:
                        st.error(f"❌ فشل الرفع: {response.text}")
            except Exception as e:
                st.error(f"❌ خطأ في الرفع: {str(e)}")
    
    st.divider()
    
    # Session management
    st.subheader("🔧 إدارة الجلسات")
    
    try:
        sessions_response = requests.get(f"{API_BASE_URL}/sessions", timeout=5)
        if sessions_response.status_code == 200:
            sessions_data = sessions_response.json()
            st.info(f"🔗 الجلسات النشطة: {sessions_data['active_sessions']}")
            
            if sessions_data['sessions']:
                st.write("**الجلسات:**")
                for session in sessions_data['sessions']:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.text(f"🔑 {session}")
                    with col2:
                        if st.button("🗑️", key=f"delete_{session}", help="حذف الجلسة"):
                            try:
                                delete_response = requests.delete(f"{API_BASE_URL}/sessions/{session}")
                                if delete_response.status_code == 200:
                                    st.success("✅ تم حذف الجلسة")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"خطأ: {str(e)}")
        else:
            st.error("❌ لا يمكن جلب معلومات الجلسات")
    except Exception as e:
        st.error(f"❌ خطأ: {str(e)}")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.8em;'>
    🤖 Document AI Service Agent v3.0 | Enhanced with Request Tracking & Validation
</div>
""", unsafe_allow_html=True)