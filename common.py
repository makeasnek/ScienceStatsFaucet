# This file contains common functions used by other files (main.py, daily.py, etc)
import re,json,datetime
from typing import List,Union,Dict,Tuple
from requests.auth import HTTPBasicAuth
import requests
from typing import Union,List,Dict,Set,Tuple
import redis
def sanitize_url(input_url:str)->str:
    """
    Quick and dirty way to sanitize a URL
    :param input_url:
    :return:
    """
    step1=re.sub('[^A-Z,0-9,//:\\?=\._]','',input_url,flags=re.MULTILINE|re.IGNORECASE)
    step2=re.sub('\n','',step1,flags=re.MULTILINE|re.IGNORECASE)
    return step2
def user_above_minimum(user:Dict[str,str],mag_per_rac:float,padding:float,faucet_amount:float)->Union[float,bool]:
    """
    m = mag/rac (this you should be able to compute from the magnitude for the project divided by the total RAC for the project)
    u = GRC/day/mag = 1/4
    n = number of days since crunch start (real number decimal days)
    C = TC / n = number of credits per day (assumed constant)
    S = 2^(6/7) * (1 - 2^(-n/7)) / (2^(6/7) - 2) + n (this is the dimensionless form of the summation taking into account the buildup)
    Then
    Est GRC equiv earned if already solo = m * u * C * S
    I think the create_time should be ok.
    Should be epoch, which means n = (current time - create time) / 86400.
    so then as long as m * u * C * S > faucet_amount, we should be good
    """
    import time
    current_time= int(time.time())
    m= mag_per_rac
    u= .25
    n = (current_time - float(user['create_time']))/86400
    tc=float(user['total_credit'])
    C = tc/n
    S = 2**(6/7)*(1-2**(-n/7))/(2**(6/7)-2)+n
    est_grc_solo_amount=m*u*C*S
    padded_amount=faucet_amount+(faucet_amount*padding)
    if est_grc_solo_amount>padded_amount:
        print(
            'CPID {} w/ {}TC and {} RAC over {} days. Predicting user would have earned {} GRC with this amount of work. Faucet amount is {}. User qualifies for faucet'.format(
                user['cpid'], int(tc), C, n, est_grc_solo_amount, faucet_amount))
        return True
    print(
        'CPID {} w/ {}TC and {} RAC over {} days. Predicting user would have earned {} GRC with this amount of work. Faucet amount is {}. User does not qualify for faucet'.format(
            user['cpid'], int(tc), C, n, est_grc_solo_amount, faucet_amount))
    return est_grc_solo_amount
def sanitize_address(input_str:str)->str:
    """
    Quick and dirty way to sanitize a URL
    :param input_str:
    :return:
    """
    return re.sub('[^A-Z,1-9]','',input_str,flags=re.MULTILINE|re.IGNORECASE)
def json_to_dict(user_json:str):
    return json.loads(user_json)
def dict_to_json(my_dict:dict):
    return json.dumps(my_dict)
def uid_to_cpid(redis: redis.Redis, uid: str, standardized_project_url: str)->Union[str,None]:
    """
    :param redis: redis connection
    :param uid: single uid
    :param standardized_project_url:
    :return:
    """
    user_dict_json=redis.hget("uid_table_"+standardized_project_url, uid)
    if not user_dict_json:
        return None
    user_dict=json_to_dict(user_dict_json)
    cpid=user_dict.get('cpid')
    return cpid
def ban_uid(redis:redis.Redis,uid:Union[str,Set[str]],standardized_project_url:str):
    """

    :param redis: redis connection
    :param uid: single uid or set of UIDs
    :param standardized_project_url:
    :return:
    """
    if isinstance(uid,Set):
        my_iter=uid
    else:
        my_iter=set()
        my_iter.add(uid)
    result=redis.sadd('banned_uids_' + standardized_project_url, *my_iter)
    print('')
def ban_cpid(redis:redis.Redis,cpid:Union[str,Set[str]]):
    """

    :param redis: redis connection
    :param cpid: single uid or set of CPIDs
    :param standardized_project_url:
    :return:
    """
    if isinstance(cpid,Set):
        my_iter=cpid
    else:
        my_iter=set()
        my_iter.add(cpid)
    result=redis.sadd('banned_cpids', *my_iter)
    print('')
def unban_cpid(redis:redis.Redis,cpid:str):
    """

    :param redis: redis connection
    :param cpid: single uid or set of UIDs
    :return:
    """
    redis.srem('banned_cpids',cpid)
def unban_uid(redis:redis.Redis,uid:str,standardized_project_url:str):
    """

    :param redis: redis connection
    :param uid: single uid or set of UIDs
    :param standardized_project_url:
    :return:
    """
    redis.srem('banned_uids_' + standardized_project_url, uid)

def is_uid_banned(redis: redis.Redis, uid: str, standardized_project_url: str):
    """
    :param redis: redis connection
    :param uid: single uid
    :param standardized_project_url:
    :return:
    """
    if redis.sismember('banned_uids_' + standardized_project_url,uid):
        return True
    return False
def is_cpid_banned(redis: redis.Redis, cpid: str):
    """
    :param redis: redis connection
    :param uid: single uid
    :param standardized_project_url:
    :return:
    """
    if redis.sismember('banned_cpids',cpid):
        return True
    return False
def standardize_project_url(url:str)->str:
    """
    Turn a project or profile URL into a standardized format used in DB
    :param url:
    :return:
    """
    original_url=url
    url=url.upper()
    url=url.replace('HTTPS://','')
    url=url.replace('HTTP://','')
    url = url.replace('WWW.', '')
    url = url.replace('/', '')
    url=re.sub('SHOW_USER.PHP\?USERID=\d*','',url)
    if url.endswith('/'):
        url=url[:-1]
    return url
def uid_from_url(url:str)->Union[str,None]:
    match=re.search('(show_user.php\?userid=)(\d*)',url)
    if not match:
        return None
    try:
        int(match.group(2))
    except Exception as e:
        return None
    return str(match.group(2))
def json_default(obj):
    """
    For serializing datetimes to json
    """
    if isinstance(obj, datetime.datetime):
        return { '_isoformat': obj.isoformat() }
    raise TypeError('...')
class GridcoinClientConnection:
    """
    A class for connecting to a Gridcoin wallet and issuing RPC commands. Currently quite barebones.
    """
    def __init__(self, config_file:str=None, ip_address:str='127.0.0.1', rpc_port:str='9876', rpc_user:str=None, rpc_password:str=None,):
        self.configfile=config_file #absolute path to the client config file
        self.ipaddress=ip_address
        self.rpc_port=rpc_port
        self.rpcuser=rpc_user
        self.rpcpassword=rpc_password
    def run_command(self,command:str,arguments:List[Union[str,bool]]=None)->dict:
        if not arguments:
            arguments=[]
        credentials=None
        url='http://' + self.ipaddress +':' + self.rpc_port + '/'
        headers = {'content-type': 'application/json'}
        payload = {
            "method": command,
            "params": arguments,
            "jsonrpc": "2.0",
            "id": 0,
        }
        jsonpayload=json.dumps(payload,default=json_default)
        if self.rpcuser or self.rpcpassword:
            credentials=HTTPBasicAuth(self.rpcuser, self.rpcpassword)
        response = requests.post(
            url, data=jsonpayload, headers=headers, auth=credentials)
        return response.json()
    def get_approved_project_urls(self)->List[str]:
        """
        :return: A list of UPPERCASED project URLs using gridcoin command listprojects
        """
        return_list=[]
        all_projects=self.run_command('listprojects')
        for projectname,project in all_projects['result'].items():
            return_list.append(project['base_url'].upper())
        return return_list
    def project_name_to_url(self,searchname:str)->Union[str,None]:
        """
        Convert a project name into its project url, then UPPERCASE it
        """
        all_projects = self.run_command('listprojects')
        for found_project_name, project_dict in all_projects['result'].items():
            if found_project_name.upper()==searchname.upper():
                return project_dict['base_url'].upper()
        return None
    def send_tx(self,destination:str,amount:Union[int,float]):
        credentials=None
        url='http://' + self.ipaddress +':' + self.rpc_port + '/'
        headers = {'content-type': 'application/json'}
        payload = {
            "method": 'sendfrom',
            "params": ['',destination,amount],
            "jsonrpc": "2.0",
            "id": 0,
        }
        jsonpayload=json.dumps(payload,default=json_default)
        if self.rpcuser or self.rpcpassword:
            credentials=HTTPBasicAuth(self.rpcuser, self.rpcpassword)
        response = requests.post(
            url, data=jsonpayload, headers=headers, auth=credentials)
        return response.json()
def wait_till_synced(grc_client:GridcoinClientConnection):
    """
    A function to WAIT until client is fully synced
    :param grc_client:
    :return:
    """
    from time import sleep
    while True:
        response=grc_client.run_command('getinfo')
        if isinstance(response,dict):
            sync_status=response.get('result',{}).get('in_sync')
            if sync_status==True:
                return
        sleep(1)