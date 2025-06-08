import streamlit as st
import datetime
from badminton_booking import MelbourneUniBadmintonBooking
import pandas as pd

# 直接写死用户名和密码
USERNAME = "lwh895556373@gmail.com"
PASSWORD = "lwh1509128709"

st.set_page_config(
    page_title="墨尔本大学羽毛球场地查询",
    page_icon="🏸",
    layout="wide"
)

st.title("🏸 墨尔本大学羽毛球场地查询")
st.title("Tom专用至尊自动登录版")
st.markdown("---")

# 初始化会话状态
if 'booking' not in st.session_state:
    st.session_state.booking = MelbourneUniBadmintonBooking()
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False

# 自动登录
if not st.session_state.is_logged_in:
    if st.session_state.booking.login(USERNAME, PASSWORD):
        st.session_state.is_logged_in = True
        st.success("已自动登录！")
    else:
        st.error("自动登录失败，请检查用户名和密码。")

# 主界面
if st.session_state.is_logged_in:
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
    
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    start_date_formatted = start_date.strftime('%Y-%m-%d')
    end_date_formatted = end_date.strftime('%Y-%m-%d')
    days_count = (end_date - start_date).days + 1
    
    if st.button("查询场地"):
        with st.spinner("正在查询场地信息..."):
            facilities_data = st.session_state.booking.get_available_courts(start_date_str, end_date_str)
            if not facilities_data or not facilities_data.get('facilities'):
                st.error("无法获取场地信息")
            else:
                facilities = facilities_data['facilities']
                st.subheader(f"🏸 墨尔本大学羽毛球馆 - 场地可用性摘要")
                st.caption(f"📅 查询日期: {start_date_formatted} 至 {end_date_formatted} ({days_count}天)")
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
                                    slot_info_list = []  # 新增：存储每个时段的详细信息
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
                                                slot_label = f"{start_time}-{end_time}"
                                                # 构造预订URL
                                                arrival_date = f"{date_formatted}T{start_time}:00.000Z"
                                                base_url = "https://unimelb.perfectmind.com/32617/Clients/BookMe4LandingPages/Facility"
                                                params = f"facilityId={facility_id}&arrivalDate={arrival_date}"
                                                book_url = f"{base_url}?{params}"
                                                slot_info_list.append((slot_label, book_url))
                                    with st.container():
                                        st.markdown(f"#### 📅 {date_formatted}")
                                        if slot_info_list:
                                            cols = st.columns(min(4, len(slot_info_list)))
                                            for i, (slot, book_url) in enumerate(slot_info_list):
                                                with cols[i % len(cols)]:
                                                    st.markdown(f'<a href="{book_url}" target="_blank"><button style="width:100%;background:#1976d2;color:white;border:none;padding:0.5em 0.2em;border-radius:4px;cursor:pointer;">{slot}</button></a>', unsafe_allow_html=True)
                                        else:
                                            st.markdown("<span style='color:red;'>无可用时段</span>", unsafe_allow_html=True)

                # ====== 新增：可视化时间表格（去重+自适应宽度） ======
                time_slots = []
                for h in range(8, 22):
                    time_slots.append(f"{h:02d}:00")
                    time_slots.append(f"{h:02d}:30")
                time_slots.append("22:00")
                date_list = [ (start_date + datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days_count) ]
                timetable = pd.DataFrame('', index=time_slots, columns=date_list)
                for facility in facilities:
                    facility_id = facility.get('ID', '')
                    facility_name = facility.get('Name', '未知场地')
                    if facility_id:
                        availability_data = st.session_state.booking.get_facility_availability(
                            facility_id, start_date_formatted, days_count
                        )
                        if availability_data and availability_data.get('availabilities'):
                            availabilities = availability_data['availabilities']
                            for day_data in availabilities:
                                date_raw = day_data.get('Date', '')
                                date_formatted = st.session_state.booking.parse_date_from_json(date_raw)
                                booking_groups = day_data.get('BookingGroups', [])
                                for group in booking_groups:
                                    available_spots = group.get('AvailableSpots', [])
                                    for spot in available_spots:
                                        if not spot.get('IsDisabled', False):
                                            time_info = spot.get('Time', {})
                                            duration_info = spot.get('Duration', {})
                                            start_hour = time_info.get('Hours', 0)
                                            start_minute = time_info.get('Minutes', 0)
                                            duration_hours = duration_info.get('TotalHours', 1)
                                            slot_count = int(duration_hours * 2)
                                            for i in range(slot_count):
                                                slot_hour = start_hour + (start_minute + i*30)//60
                                                slot_minute = (start_minute + i*30)%60
                                                slot_label = f"{slot_hour:02d}:{slot_minute:02d}"
                                                if slot_label in timetable.index and date_formatted in timetable.columns:
                                                    val = timetable.at[slot_label, date_formatted]
                                                    # 去重
                                                    names = set([x.strip() for x in val.split(',') if x.strip()] + [facility_name])
                                                    timetable.at[slot_label, date_formatted] = ', '.join(sorted(names))
                st.markdown("---")
                st.subheader("🗓️ 全部场地可用时间总览表")
                st.dataframe(timetable, height=700, use_container_width=True)
else:
    st.error("自动登录失败，无法查询场地信息！")