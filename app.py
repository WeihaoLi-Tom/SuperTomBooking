import streamlit as st
import datetime
from badminton_booking import MelbourneUniBadmintonBooking, load_credentials, save_credentials

st.set_page_config(
    page_title="墨尔本大学羽毛球场地查询",
    page_icon="🏸",
    layout="wide"
)

# 设置页面标题和说明
st.title("🏸 墨尔本大学羽毛球场地查询")
st.markdown("---")

# 初始化会话状态
if 'booking' not in st.session_state:
    st.session_state.booking = MelbourneUniBadmintonBooking()
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False

# 侧边栏 - 登录部分
with st.sidebar:
    st.header("🔐 登录")
    
    # 尝试加载保存的凭据
    credentials = load_credentials()
    
    if credentials and not st.session_state.is_logged_in:
        if st.button("使用保存的登录信息"):
            username = credentials['username']
            password = credentials['password']
            if st.session_state.booking.login(username, password):
                st.session_state.is_logged_in = True
                st.success("登录成功！")
                st.rerun()
    
    # 登录表单
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        remember_me = st.checkbox("记住登录信息")
        submit = st.form_submit_button("登录")
        
        if submit:
            if st.session_state.booking.login(username, password):
                st.session_state.is_logged_in = True
                if remember_me:
                    save_credentials(username, password)
                st.success("登录成功！")
                st.rerun()
            else:
                st.error("登录失败，请检查用户名和密码。")

# 主界面
if st.session_state.is_logged_in:
    # 日期选择
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "开始日期",
            value=datetime.datetime.now() + datetime.timedelta(days=1),
            min_value=datetime.datetime.now(),
            max_value=datetime.datetime.now() + datetime.timedelta(days=30)
        )
    with col2:
        end_date = st.date_input(
            "结束日期",
            value=start_date + datetime.timedelta(days=2),
            min_value=start_date,
            max_value=start_date + datetime.timedelta(days=7)
        )
    
    # 转换日期格式
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    start_date_formatted = start_date.strftime('%Y-%m-%d')
    end_date_formatted = end_date.strftime('%Y-%m-%d')
    days_count = (end_date - start_date).days + 1
    
    if st.button("查询场地"):
        with st.spinner("正在查询场地信息..."):
            # 获取场地信息
            facilities_data = st.session_state.booking.get_available_courts(start_date_str, end_date_str)
            
            if not facilities_data or not facilities_data.get('facilities'):
                st.error("无法获取场地信息")
            else:
                facilities = facilities_data['facilities']
                st.subheader(f"🏸 墨尔本大学羽毛球馆 - 场地可用性摘要")
                st.caption(f"📅 查询日期: {start_date_formatted} 至 {end_date_formatted} ({days_count}天)")
                
                # 创建场地信息表格
                available_facilities = []
                facility_data = []
                
                for facility in facilities:
                    facility_id = facility.get('ID', '')
                    facility_name = facility.get('Name', '未知场地')
                    
                    if facility_id:
                        availability_data = st.session_state.booking.get_facility_availability(
                            facility_id, start_date_formatted, days_count
                        )
                        
                        if availability_data and availability_data.get('availabilities'):
                            availabilities = availability_data['availabilities']
                            total_days_with_slots = 0
                            total_slots = 0
                            
                            for day_data in availabilities:
                                booking_groups = day_data.get('BookingGroups', [])
                                available_slots = 0
                                for group in booking_groups:
                                    for spot in group.get('AvailableSpots', []):
                                        if not spot.get('IsDisabled', False):
                                            available_slots += 1
                                
                                if available_slots > 0:
                                    total_days_with_slots += 1
                                    total_slots += available_slots
                            
                            if total_slots > 0:
                                facility_data.append({
                                    "场地": facility_name,
                                    "可用天数": total_days_with_slots,
                                    "可用时段": total_slots,
                                    "状态": "✅ 有空档"
                                })
                                available_facilities.append((facility_id, facility_name))
                            else:
                                facility_data.append({
                                    "场地": facility_name,
                                    "可用天数": 0,
                                    "可用时段": 0,
                                    "状态": "❌ 暂无可用"
                                })
                        else:
                            facility_data.append({
                                "场地": facility_name,
                                "可用天数": 0,
                                "可用时段": 0,
                                "状态": "❓ 查询失败"
                            })
                
                # 显示场地摘要表格
                st.dataframe(
                    facility_data,
                    column_config={
                        "场地": st.column_config.TextColumn("场地", width="medium"),
                        "可用天数": st.column_config.NumberColumn("可用天数", width="small"),
                        "可用时段": st.column_config.NumberColumn("可用时段", width="small"),
                        "状态": st.column_config.TextColumn("状态", width="small")
                    },
                    hide_index=True
                )
                
                # 显示详细时间段
                if available_facilities:
                    st.subheader("📋 详细可用时间段")
                    
                    for facility_id, facility_name in available_facilities:
                        with st.expander(f"🏟️ {facility_name}"):
                            availability_data = st.session_state.booking.get_facility_availability(
                                facility_id, start_date_formatted, days_count
                            )
                            
                            if availability_data and availability_data.get('availabilities'):
                                availabilities = availability_data['availabilities']
                                
                                for day_data in availabilities:
                                    date_raw = day_data.get('Date', '')
                                    date_formatted = st.session_state.booking.parse_date_from_json(date_raw)
                                    
                                    booking_groups = day_data.get('BookingGroups', [])
                                    day_slots = []
                                    
                                    for group in booking_groups:
                                        available_spots = group.get('AvailableSpots', [])
                                        
                                        for spot in available_spots:
                                            if not spot.get('IsDisabled', False):
                                                time_info = spot.get('Time', {})
                                                duration_info = spot.get('Duration', {})
                                                
                                                start_hour = time_info.get('Hours', 0)
                                                start_minute = time_info.get('Minutes', 0)
                                                duration_hours = duration_info.get('TotalHours', 1)
                                                
                                                start_time = f"{start_hour:02d}:{start_minute:02d}"
                                                end_hour = start_hour + int(duration_hours)
                                                end_minute = start_minute + int((duration_hours % 1) * 60)
                                                if end_minute >= 60:
                                                    end_hour += 1
                                                    end_minute -= 60
                                                end_time = f"{end_hour:02d}:{end_minute:02d}"
                                                
                                                day_slots.append(f"{start_time}-{end_time}")
                                    
                                    if day_slots:
                                        st.write(f"📅 {date_formatted}: {', '.join(day_slots)}")
                                    else:
                                        st.write(f"📅 {date_formatted}: 无可用时段")
else:
    st.info("请先在左侧登录以查询场地信息") 