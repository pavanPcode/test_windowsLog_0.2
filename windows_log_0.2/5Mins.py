import time
import requests
from datetime import datetime,timedelta
#from write_in_windows_events import event_viewer_log,starting_event_TEST
#from read_from_txt_file import read_data_from_file
import mysql.connector
import base64
#import post_Active_transactions
#from post_Active_transactions import check_active_requests,db_update_record
date = datetime.now()
import win32evtlog

import mysql.connector
import requests
import base64

db_config = {}
with open('db_config.txt', 'r') as file:
    for line in file:
        key, value = line.strip().split('=')
        db_config[key.strip()] = value.strip()
host=db_config['host']
username=db_config['user']
password=db_config['password']
database=db_config['database']

def db_update_record(sql_query):
    try:
        # MySQL connection settings
        conn = mysql.connector.connect(
            host=host,
            user=username,
            password=password,
            database=database
        )

        cursor = conn.cursor()

        cursor.execute(sql_query)
        conn.commit()  # Commit the changes to the database

        conn.close()
        return "Record updated successfully.", 200
    except mysql.connector.Error as e:
        return {'error': str(e)}, 400  # Handle database errors
    except Exception as e:
        return {'error': str(e)}, 500  # Handle other exceptions

def dbgetlasttransactions(sql_query):
    try:
        # MySQL connection settings
        conn = mysql.connector.connect(
            host=host,
            user=username,
            password=password,
            database=database
        )

        # Connect to the MySQL database
        cursor = conn.cursor()

        cursor.execute(sql_query)

        # Fetch all the data
        data = cursor.fetchall()

        if not data:
            return []

        # Create a list of dictionaries, where each dictionary represents a record
        result_list = []
        for row in data:
            result_dict = {}
            for column_name, value in zip(cursor.column_names, row):
                result_dict[column_name] = value
            result_list.append(result_dict)

        conn.close()
        return result_list
    except mysql.connector.Error as e:
        return {'error': str(e)}, 400  # Handle database errors
    except Exception as e:
        return {'error': str(e)}, 500  # Handle other exceptions

def call_post_api(url,data,refno):
    try:
        # print(url)
        result = {
        "gm_transaction_id": refno,
        "vehicle_numberplate_b64": data['numberPlateImageb64'],
        "vehicle_image_b64": data['vehicleImageb64'],
        "cardId": data['cardId'],
        "dateOfTransaction": data['dateOfTransaction'],
        "plate_path": data['numberPlateImage']
        }
        # Define the file to upload
        files = {
        "vehicle_numberplate": open(data['numberPlateImage'], "rb"),
        "vehicle_image": open(data['vehicleImage'], "rb")
        }

        # Send the POST request with form data and the file
        response = requests.post(url, data=result, files=files)

        # Check the response
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        return False

def convert_image_to_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            # Read the image binary data
            image_binary = image_file.read()
            # Encode the binary data as base64
            base64_encoded = base64.b64encode(image_binary).decode('utf-8')

            return base64_encoded
    except Exception as e:
        print(f"Error converting image to base64: {str(e)}")

        return None


# sql_quary_get_vehcle_details = """SELECT vt.id id,vt.machineId machineId, vt.DeviceId deviceId,vt.CardId cardId,vt.dateOfTransaction dateOfTransaction,
# vti.VehicleImage vehicleImage, vti.VehicleImage numberPlateImage,'' numberPlateImageb64,'' vehicleImageb64
# FROM VehicleTransaction vt
# INNER JOIN VehicleTransactionImage vti ON vt.id = vti.VehicleTransactionId
# WHERE dateOfTransaction BETWEEN DATE_SUB('{0}', INTERVAL {1} SECOND) and '{0}'
# order by DateOfTransaction  limit 1"""

sql_quary_get_vehcle_details = """(SELECT vt.id AS id,
       vt.machineId AS machineId,
       vt.DeviceId AS deviceId,
       vt.CardId AS cardId,
       vt.dateOfTransaction AS dateOfTransaction,
       vti.VehicleImage AS vehicleImage,
       vti.VehicleImage AS numberPlateImage,
       '' AS numberPlateImageb64,
       '' AS vehicleImageb64
FROM VehicleTransaction vt
INNER JOIN VehicleTransactionImage vti ON vt.id = vti.VehicleTransactionId
WHERE vt.dateOfTransaction BETWEEN DATE_SUB('{0}', INTERVAL {1} SECOND) AND '{0}'
ORDER BY dateOfTransaction desc limit 1)
UNION all
 (SELECT vt.id AS id,
       vt.machineId AS machineId,
       vt.DeviceId AS deviceId,
       vt.CardId AS cardId,
       vt.dateOfTransaction AS dateOfTransaction,
       vti.VehicleImage AS vehicleImage,
       vti.VehicleImage AS numberPlateImage,
       '' AS numberPlateImageb64,
       '' AS vehicleImageb64
FROM VehicleTransaction vt
INNER JOIN VehicleTransactionImage vti ON vt.id = vti.VehicleTransactionId
WHERE vt.dateOfTransaction BETWEEN  '{0}'  AND date_add('{0}', INTERVAL {2} SECOND)
ORDER BY dateOfTransaction limit 1) limit 1
"""


def check_active_requests(url,requestSendInSeconds,requestSendInSecondsPlus):
    RequestVehicle = dbgetlasttransactions("select * from RequestVehicle where isActive = 1")

    if RequestVehicle != []:
        for i in RequestVehicle:
            refno = i['RefNo']
            #print(sql_quary_get_vehcle_details.format(i['RefNoDatetime'],requestSendInSeconds,requestSendInSecondsPlus))
            data = dbgetlasttransactions(sql_quary_get_vehcle_details.format(i['RefNoDatetime'],requestSendInSeconds,requestSendInSecondsPlus))
            if data != []:
                for veh_details in data:
                    veh_details['dateOfTransaction'] = veh_details['dateOfTransaction'].strftime("%Y-%m-%dT%H:%M:%S")
                    veh_details['numberPlateImageb64'] = convert_image_to_base64(veh_details['numberPlateImage'])
                    veh_details['vehicleImageb64'] = convert_image_to_base64(veh_details['vehicleImage'])



                    api_Responce = call_post_api(url, veh_details, refno)

                    if api_Responce == True:

                        db_update_record(f"update RequestVehicle set isActive = 0,RefStatus = 2,isActive0Time = CURRENT_TIMESTAMP,vehicletransactionId = {veh_details['id']},requestSendTime = CURRENT_TIMESTAMP where id = {i['Id']}")

    return 'suss'






def read_data_from_file():
    data = {}

    # Open the file for reading
    with open('Config.txt', 'r') as file:
        for line in file:
            # Split each line into key and value pairs
            key, value = line.strip().split('=')
            # Remove leading and trailing spaces from key and value
            key = key.strip()
            value = value.strip()
            # Store the data in a dictionary
            data[key] = value

    return data

def event_viewer_log(event_id,event_strings,description):
    # Log the exception to the Windows Event Log
    log_type = 'iParkRightAnpr'  # You can change this to 'Security', 'System', etc.
    # event_id = 1005  # You can choose a unique event ID
    event_category = 0  # The category of the event (0 for none)
    # description = "Please restart your device . New Data Not Comming."
    # event_strings = [f"Exception occurred: {message}",description]

    # # Additional information for the event

    # task_category = 1  # You can choose an appropriate task category

    # Open the event log for writing
    h_log = win32evtlog.OpenEventLog(None, log_type)

    # Print parameters for debugging
    #print(f"log_type: {log_type}, event_id: {event_id}, event_category: {event_category}, event_strings: {event_strings}")

    win32evtlog.ReportEvent(h_log,win32evtlog.EVENTLOG_ERROR_TYPE,event_category,event_id,None,event_strings,None,)
    win32evtlog.CloseEventLog(h_log)


    return True



def starting_event_TEST():
    try:
        # Define your event source and log name
        # event_source = "iParkRight"
        event_log = "iParkRightAnpr"

        # Open the event log for writing
        handle = win32evtlog.OpenEventLog(None, event_log)

        # Define the event category, event ID, and event message
        event_category = 0
        event_id = 5501  # Unique event ID
        event_message = f"ANPR Services Started Successfully - {datetime.now()} "

        # Write an information event
        win32evtlog.ReportEvent(handle, win32evtlog.EVENTLOG_INFORMATION_TYPE, event_category, event_id, None,
                                (event_message,), None)

        # Close the event log handle
        win32evtlog.CloseEventLog(handle)
        return False
    except Exception as e:
        return f"An error occurred: {e}"






txt_data = read_data_from_file()
if 'get_url' in txt_data:
    url = txt_data['get_url']
if 'get_url_file_path' in txt_data:
    path = txt_data['get_url_file_path']
if 'postapiurl' in txt_data:
    postapiurl = txt_data['postapiurl']
if 'postapiurl' in txt_data:
    postapiurl = txt_data['postapiurl']
if 'delimgapiurl' in txt_data:
    delimgapiurl = txt_data['delimgapiurl']
if 'deldbrecordsapiurl' in txt_data:
    deldbrecordsapiurl = txt_data['deldbrecordsapiurl']
if 'requestSendInSeconds' in txt_data:
    requestSendInSeconds = txt_data['requestSendInSeconds']
if 'requestSendInSecondsPlus' in txt_data:
    requestSendInSecondsPlus = txt_data['requestSendInSecondsPlus']

try:
    start_event_log = starting_event_TEST()
except:
    pass

end_time = datetime.now() + timedelta(days=30)
while datetime.now() < end_time:

    try:
        try:
            f = check_active_requests(postapiurl,requestSendInSeconds,requestSendInSecondsPlus)
            response = requests.post(delimgapiurl)
            response = requests.post(deldbrecordsapiurl)
            c = db_update_record("""UPDATE requestvehicle SET isActive  = 0 ,RefStatus = 3,isActive0Time = CURRENT_TIMESTAMP  WHERE DATE(RefNoDatetIME) != CURDATE() and RefStatus = 1 and isActive = 1 ;""")
            # print(c)
        except:
            pass


        response = requests.get(url)

        data = response.json()
        data['vehicleImage'],data['numberPlateImage'],data['numberPlateImageb64'],data['vehicleImageb64'] = '','','',''

        with open(path, 'a') as file:
            file.write(f" {str(datetime.now())} :  {data}    " + '\n' + '----------------------------------------------------------------------' + '\n')

        cardId = data['cardId']
        dateOfTransaction = data['dateOfTransaction']
        # Convert the string to a datetime object
        dt1 = datetime.fromisoformat(dateOfTransaction)

        # Get the current time as a datetime object
        current_time = datetime.now()

        # Calculate the difference in hours
        time_difference = (current_time - dt1).total_seconds() / 3600

        if time_difference > 18:
            event_id =  5505
            event_strings = """(Error) ANPR Service Attention Required  1005 """
            description = f""" 
------------------------------------------------------------------------------------
VehicleNo:  {cardId}
Transaction Date: {dateOfTransaction}
------------------------------------------------------------------------------------
Recommed you to verify LAN Connectivity,ANPR Camera power, contact your administrator """

            event_viewer_log(event_id,event_strings,description)
            # windows_not('Anpr',f"Stored date is more than 24 hours old. last dated on {dateOfTransaction} for vehcle {cardId}")

            with open(path, 'a') as file:
                file.write(
                    f" {str(datetime.now())} :  error raised in event viewer    " + '\n' + '----------------------------------------------------------------------' + '\n')


    except requests.exceptions.RequestException as e:
        event_viewer_log(5510, 'ANPR Services Stopped ', 'ANPR Services Stoppedslnfd ')
        with open(path, 'a') as file:
            file.write(f" {str(datetime.now())} : Error :  {e}    " + '\n' + '----------------------------------------------------------------------' + '\n')

    # Wait for 5 minutes
    time.sleep(300)  # 5 minutes in seconds
