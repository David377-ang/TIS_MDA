import os
import re
import json
import requests
from datetime import datetime
import csv
import subprocess
import time
import pywinusb.hid as hid
import traceback


def show_msg(fixtureID):
    subprocess.Popen(["python", "-c", f"""
import tkinter as tk
from tkinter import messagebox
root = tk.Tk()
root.withdraw()
messagebox.showinfo("Reminder", "The fixture [{fixtureID}] has been Shutdown!!!\\n"
                        "After confirming that the fixture can be tested stably, \\n"
                        "go to the MARS system to release the shutdown status!!\\n"
                        "If have any question, please contact Ray Bai ")
"""])


def Upload_to_TIS_Fake(param, random_sn, log_name):
    # OA:10.249.201.16
    # TE:172.18.1.16
    url = "http://10.239.170.17:8088/api/v1/register/"
    if param[0] == "Monica" or param[0] == "Meta" or param[0] == "AWS":
        url = url + "save" + param[0] + "ICT"
    else:
        url = url + "saveOthersICT"
    with open("D:/TIS/Info.txt", 'r', encoding='utf-8') as file:
        lines = file.readlines()
    if lines:
        file_content = ''.join(lines[1:])
    data_info = json.loads(file_content)
    data = {
        "area": "",
        "projectLine": "",
        "projectSpace": "",
        "stage": "MDA",
        "version": "",
        "fixtureSerialNumber": "",
        "boxNumber": "",
        "customer": param[0],
        "projectModel": param[1],
        "projectProduct": param[2],
        "projectFixture": param[3],
        "projectPartNumber": "",
        "motherBoardSerialNumber": random_sn,
        "bmcBbSerialNumber": "",
        "operatorId": "99999999",
        "logName": log_name,
        "sub": "",
        "testResult": "PASS",
        "fixtureUseCount": data_info["fixtureUseCount"] + "/"
    }
    content = json.dumps(data, ensure_ascii=False, indent=2)
    # return 999, content
    response = requests.post(url, json=data, timeout=(5, 10))
    return response.status_code, content


def Upload_to_TIS(slot, result, sn, filename, test_result, operID):
    with open("D:/TIS/Info.txt", 'r', encoding='utf-8') as file:
        lines = file.readlines()
    if lines:
        file_content = ''.join(lines[1:])
    data_info = json.loads(file_content)

    with open(os.getcwd() + "/Info.txt", 'r', encoding='utf-8') as file:
        lines = file.readlines()
    file_content = ''.join(lines[1:])
    data = json.loads(file_content)
    if lines:
        url_line = lines[0].strip()
        _, url = url_line.split('=')
        url = url.strip()
        if data["customer"] == "Monica" or data["customer"] == "Meta" or data["customer"] == "AWS":
            url = url + "save" + data["customer"] + "ICT"
        else:
            url = url + "saveOthersICT"
    data["stage"] = "IA"
    data["motherBoardSerialNumber"] = sn
    data["logName"] = filename
    data["projectFixture"] = data["projectFixture"] + "-" + str(slot)
    data["sub"] = "NULL"
    data["operatorId"] = operID
    # data["testResult"] = test_result
    data["testResult"] = Counting_Fail_times(
        data["projectProduct"], test_result, data["projectFixture"], sn, operID, filename)
    machine_number = data_info["fixtureUseCount"]
    fixtureUseCount = read()
    data["fixtureUseCount"] = machine_number + "/" + fixtureUseCount

    if result != "":
        result_str = result
        result = json.loads(result_str) if isinstance(
            result_str, str) else result_str
        data["detailList"] = result
    Update_status_to_MARS(machine_number, data["testResult"], data["logName"])
    Upload_json_to_ATE(data)
    content = json.dumps(data, ensure_ascii=False, indent=2)
    # return 999, content
    response = requests.post(url, json=data, timeout=(5, 10))
    return response.status_code, content


def Counting_Fail_times(product, result, fixtureID, SN, employee_id, log_name):
    file_path = "D:/TIS/" + product + "/"
    os.makedirs(file_path, exist_ok=True)
    current_time = datetime.now()
    time_str = current_time.strftime("%Y-%m-%d")
    file_name = file_path + "FAIL-STOP_" + \
        time_str + ".txt"
    time_str = current_time.strftime("%Y-%m-%d %H:%M:%S\n")
    with open(file_name, "a", encoding="utf-8") as file_STOP:
        if result == "FAIL":
            if os.path.exists(file_path + fixtureID + "_" + "2.txt"):
                result = "FAIL-STOP"
                str = fixtureID + " : 3rd Fail\nSN : " + SN + "\nEmployee_ID : " + \
                    employee_id + "\nLog Name : " + log_name + "\n"
                Log_ouput(file_STOP, str, time_str)
            elif os.path.exists(file_path + fixtureID + "_" + "1.txt"):
                with open(file_path + fixtureID + "_" + "2.txt", "a", encoding="utf-8") as file:
                    pass
                str = fixtureID + " : 2nd Fail\nSN : " + SN + "\nEmployee_ID : " + \
                    employee_id + "\nLog Name : " + log_name + "\n"
                Log_ouput(file_STOP, str, time_str)
            else:
                with open(file_path + fixtureID + "_" + "1.txt", "a", encoding="utf-8") as file:
                    pass
                str = fixtureID + " : 1st Fail\nSN : " + SN + "\nEmployee_ID : " + \
                    employee_id + "\nLog Name : " + log_name + "\n"
                Log_ouput(file_STOP, str, time_str)
        else:
            for filename in os.listdir(file_path):
                if filename.startswith(fixtureID):
                    path = os.path.join(file_path, filename)
                    os.remove(path)
            str = fixtureID + " : PASS\nSN : " + SN + "\nEmployee_ID : " + \
                employee_id + "\nLog Name : " + log_name + "\n"
            Log_ouput(file_STOP, str, time_str)
    return result


def Log_analysis(path, filename):
    common_list = ["R", "C", "D", "Q", "QF", "U", "J"]
    specail_list = ["TPG", "ANL"]

    with open(path + filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    test_result = lines[2].split(",")[0]
    sn = lines[2].split(",")[4]
    data = []
    open_short_list = []

    if test_result == "SKIP":
        return "", test_result, "", ""
    with open(path + filename, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for _ in range(6):
            next(reader)

        for row in reader:
            # print(row)
            if not any(row):
                continue
            elif "// Short_Data" in row or "// Open_Data" in row:
                continue
            elif "Short <" in row[0]:
                open_short_list.append(row[0])
            elif "Open <" in row[0]:
                open_short_list.append(row[0])
            else:
                data.append({
                    'StepNum': row[0],
                    'PartName': row[1],
                    'Type': row[2],
                    'Act_V': row[3],
                    'Std_V': row[4],
                    'HLim': row[5],
                    'LLim': row[6],
                    'Msr_V': row[7],
                    'Result': row[8]
                })

        slot = 1
        if any("#2" in row['PartName'] for row in data):
            slot = 2
        if any("#3" in row['PartName'] for row in data):
            slot = 3
        if any("#4" in row['PartName'] for row in data):
            slot = 4

    if test_result == "FAIL":
        result_data = [row for row in data if row['Result'].strip() == '1']
        for row in result_data:
            if "#1" in row["PartName"]:
                row["PartName"] = row["PartName"].replace("#1", "")
            elif "#2" in row["PartName"]:
                row["PartName"] = row["PartName"].replace("#2", "")
            elif "#3" in row["PartName"]:
                row["PartName"] = row["PartName"].replace("#3", "")
            elif "#4" in row["PartName"]:
                row["PartName"] = row["PartName"].replace("#4", "")
            else:
                row["PartName"] = row["PartName"].replace("#1", "")

        result = []
        for row in result_data:
            if row["Type"].strip() in common_list:
                if row["HLim"].strip() == "-1.0":
                    value = f"[{row['LLim'].strip()}%, {round_with_unit(row['Act_V'].strip())}, Infinite]," \
                        f"{round_with_unit(row['Msr_V'].strip())}"
                else:
                    value = f"[{row['LLim'].strip()}%, {round_with_unit(row['Act_V'].strip())}, " \
                        f"{row['HLim'].strip()}%],{round_with_unit(row['Msr_V'].strip())}"
            elif row["Type"].strip() in specail_list:
                value = "NULL"
            elif row["Type"].strip() == "TJT":
                value = f"[{round_with_unit(row['Std_V'].strip())}, {round_with_unit(row['Act_V'].strip())}]," \
                    f"{round_with_unit(row['Msr_V'].strip())}"
            else:
                value = "Error"

            content = TIS_format(slot="NULL", location=row["PartName"].strip(),
                                 pin=row["Type"].strip(), value=value)
            result.append(content)

        pattern = r"(\w+)\s<([^>]+)>\s<([^>]+)>"
        for row in open_short_list:
            match = re.match(pattern, row)
            if match:
                part1 = match.group(1)
                part2 = match.group(2).replace(" ", ",").strip(",")
                part3 = match.group(3).replace(" ", ",").strip(",")

                content = TIS_format(slot="NULL", location=part1,
                                     pin=part1, value="[" + part2 + "],[" + part3 + "]")
                result.append(content)

        json_result = json.dumps(
            [item.__dict__ for item in result], ensure_ascii=False, indent=2)
    else:
        json_result = ""

    return slot, test_result, sn, json_result

def Upload_json_to_ATE(json_data):
    # TE:172.18.252.2
    # OA:10.249.206.46
    url = 'http://172.18.252.2:5000/upload_tis_log'
    json_str = json.dumps(json_data)
    data = {
            "motherBoardSerialNumber": json_data["motherBoardSerialNumber"],
            "FixtureID": json_data["projectFixture"],
            "Test_Result": json_data["testResult"],
            "Log_Name": json_data["logName"],
            "json_data": json_str
    }
    content = json.dumps(json_data, ensure_ascii=False, indent=2)
    # return 999, content
    try:
        response = requests.post(url, json=data, timeout=(5, 10))
    except Exception:
        error_info = traceback.format_exc()
        file_path = "D:/TIS/Debug/"
        os.makedirs(file_path, exist_ok=True)
        with open(file_path + "SN_Count_Error.txt", "a", encoding="utf-8") as file:
            
            file.write(content)
            time_str = datetime.now().strftime("\n%Y-%m-%d %H:%M:%S\n")
            file.write(time_str)
            file.write(error_info)
            file.write("==================================================\n")

def Request_to_MARS():
    with open("D:/TIS/Info.txt", 'r', encoding='utf-8') as file:
        lines = file.readlines()
    if lines:
        file_content = ''.join(lines[1:])
    data = json.loads(file_content)
    machine_number = data["fixtureUseCount"]
    # OA:10.249.201.17
    # TE:172.18.1.17
    url = 'http://172.18.1.17:8085/api/projectsFact/checkAndSetFixtureStatusICT?projectFixture=' + machine_number
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*"
    }
    try:
        response = requests.get(url, headers=headers, timeout=(5, 10))
    except Exception:
        return machine_number, "1"
    return machine_number, response.text
    # return machine_number, "9"


def Update_status_to_MARS(machine_number, result, logname):
    if result == 'FAIL-STOP':
        statusCode = '9'
        str = "The Machine : " + machine_number + \
              " has failed three times continuously!!!\n"
    else:
        statusCode = '0'
        str = "The Machine : " + machine_number + \
              "\nTesting result : " + result + "!!!\n"

    # OA:10.249.201.17
    # TE:172.18.1.17
    url = 'http://172.18.1.17:8085/api/projectsFact/postFixtureStatus?projectFixture=' + \
        machine_number + '&statusCode=' + statusCode + '&description=' + logname
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*"
    }
    try:
        requests.get(url, headers=headers, timeout=(5, 10))
    except Exception:
        str = "The MARS system reply timeout!!!"

    file_path = "D:/TIS/MARS/"
    os.makedirs(file_path, exist_ok=True)
    time_str = datetime.now().strftime("%Y%m%d")
    file_name = file_path + "MARS_log_" + time_str + ".txt"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S\n")
    with open(file_name, "a", encoding="utf-8") as file_STOP:
        Log_ouput(file_STOP, str, time_str)


def Log_ouput(file_STOP, str, time_str):
    file_STOP.write(str)
    file_STOP.write(time_str)
    file_STOP.write(
        "========================================\n")


def round_with_unit(value):
    import re
    match = re.match(r"([-+]?\d*\.\d+|\d+)([a-zA-Z]*)", value)
    if match:
        num_part = float(match.group(1))
        unit_part = match.group(2)
        rounded_num = round(num_part, 2)
        return f"{rounded_num}{unit_part}"
    else:
        return value


class TIS_format:
    def __init__(self, slot, location, pin, value):
        self.slot = slot
        self.location = location
        self.pin = pin
        self.value = value


def read():
    mywriter = HIDWriter()
    if mywriter.initialized:
        basc_data = mywriter.read()
        open('counter.ini', 'w').write(basc_data.strip())
        mywriter.close()
    with open("counter.ini", "r", encoding="utf-8") as f:
        content = f.read()
    count_match = re.search(r'Count=(.*)', content)
    if count_match:
        count = count_match.group(1)
    return count


class HIDWriter(object):

    def __init__(self, vid=0xCD12, pid=0xC001):
        self.initialized = False
        _filter = hid.HidDeviceFilter(vendor_id=vid, product_id=pid)
        devs = _filter.get_devices()
        if len(devs) > 0:
            self.dev = devs[0]
            self.dev.open()
            self.reports = self.dev.find_output_reports()
            self.initialized = True
        else:
            # print('Counter NOT FOUND!')
            basc_data = '''
Count=%s\nFixture_ID=%s\nMaintenance_time=%s\n\
Maintenance_count=%s\nCount_limit=%s\nResult=0
            ''' % ('N/A', 'N/A', 'N/A', 'N/A', 'N/A')
            open('counter.ini', 'w').write(basc_data.strip())
            # sys.exit(-1)

        if self.initialized:
            self.write_status = []

            # write for the first time to ensure following writes succed
            send_list = [0x00, 0x1f, 0x11] + [0x00] * 29 + [0x0d]
            self.reports[0].set_raw_data(send_list)
            result = self.reports[0].send()
            time.sleep(1)

    def read(self):
        '''
        read the input from HID device
        '''
        fixture_id_list = self.write([0x11])
        rest_list = self.write([0x12])
        fixture_id = self.int_list_to_str(fixture_id_list[3:32])
        count = self.int_list_to_str(rest_list[3:7])
        maintenance_time = self.int_list_to_str(rest_list[7:15])
        maintenance_count = self.int_list_to_str(rest_list[15:19])
        count_limit = self.int_list_to_str(rest_list[19:23])

        basc_data = '''
Count=%s\nFixture_ID=%s\nMaintenance_time=%s\n\
Maintenance_count=%s\nCount_limit=%s\nResult=%d
        ''' \
        % (count, fixture_id, maintenance_time,
           maintenance_count, count_limit,
           min(self.write_status))

        return basc_data

    def write(self, cmd):
        prefix = [0x00, 0x1f]
        postfix = [0x0d]
        send_list = prefix + cmd + [0x00] * (30-len(cmd)) + postfix
        self.dev.set_raw_data_handler(self._handle_raw_data)
        self.reports[0].set_raw_data(send_list)
        result = self.reports[0].send()
        self.received_data = None
        for i in range(5):
            if self.received_data != None:
                break
            time.sleep(0.1)
        if not self.received_data or \
                self.received_data[2] != cmd[0] or \
                self.received_data[-1] != 0x50:
            self.write_status.append(0)
            # print(hex(cmd[0]) + ' write FAIL')
        else:
            self.write_status.append(1)
            # print(hex(cmd[0]) + ' write OK')

        return self.received_data

    def close(self):
        self.dev.close()

    def _handle_raw_data(self, data):
        self.received_data = data

    def int_list_to_int_str(self, int_list):
        ''' 
        convert a integer list to a hex string list,
        then convert the hex string list to a int string    
        '''
        # int list to hex string list
        hex_str_list = [hex(i)[2:].zfill(2) for i in int_list]
        # concat the hex_str_list into a string
        _str = ''.join(hex_str_list)

        return str(int(_str, 16))

    def int_list_to_str(self, int_list):
        '''
        convert a list of ints a string
        '''
        if len(int_list) < 8:
            return self.int_list_to_int_str(int_list)

        str_list = [chr(i) for i in int_list]
        _str = ''.join(str_list)
        return _str.strip('\x00')
