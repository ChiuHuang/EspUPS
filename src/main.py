import httpx
import flet as ft
import flet_charts as fch 
import datetime
import asyncio
import dotenv
import os
dotenv.load_dotenv()

def main(page: ft.Page):
    page.title = "UPS Monitor"
    page.theme_mode = ft.ThemeMode.LIGHT 

    chart_data = fch.LineChartData(
        points=[],  
        stroke_width=3,
        color=ft.Colors.BLUE_400,
        curved=True,
        rounded_stroke_cap=True, 
    )

    chart = fch.LineChart(
        data_series=[chart_data],
        border=ft.Border(
            bottom=ft.BorderSide(2, ft.Colors.GREY_400),
            left=ft.BorderSide(2, ft.Colors.GREY_400),
        ),
        left_axis=fch.ChartAxis(
            title=ft.Text("Voltage (V)", weight=ft.FontWeight.BOLD),
            label_size=40,
        ),
        bottom_axis=fch.ChartAxis(
            labels=[], 
            label_size=32, 
        ),
        expand=True,
        min_y=0,
        max_y=15,
    )
    
    voltshow = ft.Text("Voltage: -- V", size=20, weight=ft.FontWeight.BOLD)
    batterypcntshow = ft.Text("Battery: --%", size=20, weight=ft.FontWeight.BOLD)
    upsshow = ft.Text("UPS Status: --", size=20, weight=ft.FontWeight.BOLD)

    SEC_TOKEN = os.getenv("SEC_TOKEN")
    BASE_URL = os.getenv("BACKEND_URL")
    USER_PASSWORD = os.getenv("USER_PASSWORD")
    async def send_command(r1, r2):
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"{BASE_URL}/SetRelay", json={
                    "secToken": SEC_TOKEN,
                    "r1": r1,
                    "r2": r2
                })
                toast = ft.SnackBar(
                    content=ft.Text("Command sent successfully"),
                    open=True
                )
                page.overlay.append(toast)
                page.update()
            except Exception as e:
                print(f"Failed to set relay: {e}")
                toast = ft.SnackBar(
                    content=ft.Text("Failed to send command"),
                    open=True
                )
                page.overlay.append(toast)
                page.update()

    current_action = None

    def on_password_confirm(e):
        if password_input.value == USER_PASSWORD:
            password_dialog.open = False
            password_input.value = ""
            page.update()
            if current_action:
                current_action()
        else:
            password_input.error_text = "Incorrect password"
            page.update()

    password_input = ft.TextField(
        label="Password", 
        password=True, 
        can_reveal_password=True,
        on_submit=on_password_confirm
    )

    password_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Security Verification"),
        content=ft.Column([
            ft.Text("Please enter the security token to continue."),
            password_input
        ], tight=True),
        actions=[
            ft.Button(content=ft.Text("Confirm"), on_click=on_password_confirm),
            ft.TextButton(content=ft.Text("Cancel"), on_click=lambda _: setattr(password_dialog, "open", False) or page.update()),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(password_dialog)

    def ask_password(action):
        nonlocal current_action
        current_action = action
        password_input.error_text = None
        password_input.value = ""
        password_dialog.open = True
        page.update()

    async def do_off(e):
        off_dialog.open = False
        page.update()
        ask_password(lambda: page.run_task(send_command, 1, 1))

    off_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirm Power Off"),
        content=ft.Text("Are you sure you want to cut all power? This is dangerous!"),
        actions=[
            ft.Button(content=ft.Text("Yes, Cut Power"), on_click=do_off, bgcolor=ft.Colors.RED, color=ft.Colors.WHITE),
            ft.TextButton(content=ft.Text("Cancel"), on_click=lambda _: setattr(off_dialog, "open", False) or page.update()),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(off_dialog)
    
    pwrstatus = ft.Text(f"Current Power Mode: ", size=20, weight=ft.FontWeight.BOLD)
    pwrtext = ft.Text("Set Power Mode:", size=20, weight=ft.FontWeight.BOLD)
    pwrbat = ft.Button(content=ft.Text("Battery Power"), icon=ft.Icons.BATTERY_FULL, on_click=lambda _: ask_password(lambda: page.run_task(send_command, 1, 0)))
    pwrwall = ft.Button(content=ft.Text("Wall Power"), icon=ft.Icons.POWER, on_click=lambda _: ask_password(lambda: page.run_task(send_command, 0, 1)))
    pwrboth = ft.Button(content=ft.Text("Bat + Wall"), icon=ft.Icons.POWER_INPUT, on_click=lambda _: ask_password(lambda: page.run_task(send_command, 0, 0)))
    pwroff = ft.Button(content=ft.Text("No Power (Dangerous)"), icon=ft.Icons.POWER_OFF, on_click=lambda _: setattr(off_dialog, "open", True) or page.update())
    timeselect = ft.SegmentedButton(
            selected_icon=ft.Icon(ft.Icons.CHECK_SHARP),
            selected=["rt"],
            allow_multiple_selection=False,
            on_change=lambda e: page.update(), # make it update immediately on selection change or it will wait 5 seconds 
            segments=[
                ft.Segment(
                    value="rt",
                    label=ft.Text("Real Time"),
                ),
                ft.Segment(
                    value="1",
                    label=ft.Text("24h"),
                ),
                ft.Segment(
                    value="7",
                    label=ft.Text("7d"),
                ),
                ft.Segment(
                    value="30",
                    label=ft.Text("30d"),
                ),
            ],
        )
    page.add(
        ft.SafeArea(
            ft.Container(
                content=ft.Column([
                    voltshow,
                    batterypcntshow,
                    upsshow,
                    pwrstatus,
                    pwrtext,
                    ft.Row([pwrbat, pwrwall, pwrboth, pwroff], wrap=True, alignment=ft.MainAxisAlignment.CENTER),
                    timeselect,
                    ft.Container(content=chart, expand=True, padding=10) 
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment.TOP_CENTER,
            ),
            expand=True,
        )
    )
    async def update_loop():
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    selected = timeselect.selected[0] if timeselect.selected else "rt"
                    if selected == "rt":
                        res = await client.post(f"{BASE_URL}/GetData", json={"range": 400})
                    elif selected in ["1", "7", "30"]:
                        days = int(selected)
                        now_ts = int(datetime.datetime.now().timestamp())
                        from_ts = now_ts - days * 24 * 3600
                        res = await client.post(f"{BASE_URL}/GetData", json={"TSFROM": from_ts, "TSTO": now_ts, "maxPoints" : 400})
                    else:
                        res = await client.post(f"{BASE_URL}/GetData", json={"range": 400})
                    
                    if res.status_code != 200:
                        print(f"Server error {res.status_code}: {res.text}")
                        data = [{"v": 0.0, "p": 0, "chg": False, "ts": 0, "possibleMode": "UNKNOWN"}]
                    else:
                        data = res.json()
                except Exception as e:
                    print(f"Network fail: {e}")
                    data = [{"v": 0.0, "p": 0, "chg": False, "ts": 0, "possibleMode": "UNKNOWN"}]

                if not data:
                    data = [{"v": 0.0, "p": 0, "chg": False, "ts": 0, "possibleMode": "UNKNOWN"}]
                
                latest = data[-1]
                is_charging = latest.get("chg", False)
                possible_mode = latest.get("possibleMode", "UNKNOWN")
                pwrstatus.value = f"Current Power Mode: {possible_mode}"
                voltshow.value = f"Voltage: {latest.get('v', 0.0):.2f} V"
                batterypcntshow.value = f"Battery: {latest.get('p', 0.0)}%"
                upsshow.value = "UPS Status: Charging" if is_charging else "UPS Status: Discharging"
                upsshow.color = ft.Colors.GREEN_400 if is_charging else ft.Colors.RED_400

                new_points = []
                new_x_labels = []
                voltages = []

                for i, d in enumerate(data):
                    v = d.get("v", 0.0)
                    voltages.append(v)
                    ts_str = datetime.datetime.fromtimestamp(d.get("ts", 0)).strftime('%M:%S')
                    
                    new_points.append(fch.LineChartDataPoint(i, v))
                    
                    # Label every 4 points
                    if i % 4 == 0:
                        new_x_labels.append(
                            fch.ChartAxisLabel(
                                value=i, 
                                label=ft.Text(ts_str, size=12, color=ft.Colors.GREY_700)
                            )
                        )

                chart_data.points = new_points
                chart.bottom_axis.labels = new_x_labels

                # Dynamically adjust the Y-axis scale 
                min_v = min(voltages)
                max_v = max(voltages)
                chart.min_y = max(0, min_v - 0.5) 
                chart.max_y = max_v + 0.5

                voltshow.update()
                batterypcntshow.update()
                upsshow.update()
                chart.update()
                if selected == "rt":
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(5)

    page.run_task(update_loop)

ft.run(main)
