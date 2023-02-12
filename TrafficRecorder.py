import requests
import urllib3

urllib3.disable_warnings()

class TrafficRecorder:
    
    url = None

    def __init__(self, url=None):
        self.url = url

    def setUrl(self, url):
        self.url = url

    # Get Traffic Recorder Server Info
    # Tested
    def info(self):
        api_path = "/automation/Info"
        try:
            response = requests.get(self.url+api_path, verify=False)
            return (response.status_code, response.json())
        except Exception as e:
            return (500, str(e))
        

    # 
    def start_proxy(self, recordingPort, upperBound=None, encrypted=False, jsonObject=None):
        if upperBound == 0:
            upperBound = None
        query_params = {"encrypted": False}
        api_path = f"/automation/StartProxy/{recordingPort}"
        if upperBound:
            api_path += f",{upperBound}"
        if encrypted:
            query_params["encrypted"] = True
        if not jsonObject:
            response = requests.get(self.url+api_path, params=query_params, verify=False)
        else:
            headers = {"Content-Type": "application/json"}
            response = requests.post(self.url+api_path, headers=headers, params=query_params, json=jsonObject, verify=False)
        return (response.status_code, response.json())

    def stop_proxy(self, recordingPort):
        api_path = f"/automation/StopProxy/{recordingPort}"
        response = requests.get(self.url + api_path, verify=False)
        return (response.status_code, response.json())

    def stop_all_proxies(self):
        api_path = "/automation/StopAllProxies"
        response = requests.get(self.url + api_path)
        return (response.status_code, response.json())

    def certificate(self):
        api_path = "/automation/Certificate"
        response = requests.get(self.url + api_path, verify=False)
        #Since 200 responses return binary content, not json
        if response.status_code >= 200 and response.status_code < 300:
            return (response.status_code, response.content)
        return (response.status_code, response.json())

    def traffic(self, recordingPort):
        api_path = f"/automation/Traffic/{recordingPort}"
        response = requests.get(self.url + api_path, verify=False)
        #Since 200 responses return binary content, not json
        print(response.text)
        if response.status_code >= 200 and response.status_code < 300:
            return (response.status_code, response.content)
        return (response.status_code, response.json())

    # TODO
    def encrypt(self, dastConfigBytes):
        api_path = "/automation/EncryptDastConfig"
        pass

    # TODO
    def encrypt_download(self, uuid):
        api_path = f"/automation/DownloadEncryptedDastConfig/{uuid}"
        pass

## Test Code
## tr = TrafficRecorder("https://ec2amaz-44nu39t:8383")
## print(tr.info())