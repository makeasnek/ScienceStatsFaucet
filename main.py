import re
import requests,common
import xmltodict
from bs4 import BeautifulSoup
import logging,redis
import logging.handlers
import config,os
from time import sleep
log = logging.getLogger()
handler = logging.handlers.RotatingFileHandler(os.path.join(config.data_storage_dir,'server.log'),
                                                   maxBytes=10 * 1024 * 1024, backupCount=1)
log.setLevel(os.environ.get("LOGLEVEL", "DEBUG"))
formatter = logging.Formatter(fmt="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s")
handler.setFormatter(formatter)
log.addHandler(handler)
logging.info('Server starting...')
log.info("Start faucet log")

from flask import Flask,render_template,request
from flask_hcaptcha import hCaptcha
from typing import List,Dict,Tuple,Union,Type

app = Flask(__name__)
app.config['HCAPTCHA_ENABLED'] = config.HCAPTCHA_ENABLED
app.config['HCAPTCHA_SITE_KEY'] = config.HCAPTCHA_SITE_KEY
app.config['HCAPTCHA_SECRET_KEY'] = config.HCAPTCHA_SECRET_KEY
hcaptcha = hCaptcha(app)

def valid_grc_address(address: str) -> bool:
    if address == "":
        return False
    if len(address) != 34:
        return False
    if address.upper()[0] not in ['S','R']:
        return False
    return True

def valid_profile_url(url: str) -> bool:
    # EXAMPLE URLS:
    # https://escatter11.fullerton.edu/nfs/show_user.php?userid=21405
    # https://worldcommunitygrid.org/boinc/show_user.php?userid=1156028
    regexes = config.valid_profile_regexes
    match_url = url.upper().replace('HTTPS://', '').replace('HTTP://', '').replace('WWW.', '')
    if match_url.endswith('/'):
        match_url = match_url[:-1]
    for regex in regexes:
        if re.fullmatch(regex, match_url,flags=re.IGNORECASE):
            return True
    return False

def get_credit_wcg(url:str,address:str)-> Union[None,str]:
    """

    :param url: Any URL
    :return: String of credit amount or None
    """
    try:

        # request user's profile page
        response=requests.get(url)
        html_response = response.content.decode()
        found_dict=xmltodict.parse(html_response)

        # verify address matches
        name=found_dict.get('user',{}).get('name')
        if address[0:29] not in name:
            return "GRC address not found on profile page"
    except Exception as e:
        logging.error('Error getting WCG credit for user {} {}'.format(url,e))
def get_credit_nfs(url:str,address:str)-> Union[int,str]:
    """

    :param url: Any URL
    :return: Credit amount or string detailing error
    """
    try:

        # request user's profile page
        response=requests.get(url)
        html_response = response.content.decode()
        single_line_html_response = html_response.replace('\n', '')
        soup = BeautifulSoup(html_response, 'html.parser')
        tables= soup.find('table', { 'class' : 'table table-condensed table-striped' })

        # verify address matches
        address_search='<title>'+address+'</title>'
        address_match = re.search(address_search, single_line_html_response,
                          flags=re.MULTILINE|re.IGNORECASE)
        if not address_match:
            return "GRC address not found on profile page"

        # get credit
        for row in tables:
            if "TOTAL CREDIT" in str(row).upper():
                match=re.search('(<td style="padding-left:12px">)([\d,]*)',str(row),flags=re.MULTILINE|re.IGNORECASE)
                if match:
                    result=match.group(2).replace(',','')
                    return int(result)
    except Exception as e:
        return str(e)

def get_credit_amicable(url:str,address:str)-> Union[str,int]:
    """

    :param url: Any URL
    :return: Credit amount or string detailing error
    """
    try:
        # request user's profile page
        response = requests.get(url)
        html_response = response.content.decode()
        html_response=html_response.replace('\n','')

        # verify address matches
        address_search='<title>'+address+'</title>'
        address_match = re.search(address_search, html_response,
                          flags=re.MULTILINE|re.IGNORECASE)
        if not address_match:
            return "GRC address not found on profile page"

        # find user credit total
        match = re.search('(Total credit</td>        <td style="padding-left:12px" >)([\d,]*)', html_response, flags=re.MULTILINE|re.IGNORECASE)
        if match:
            result = match.group(2).replace(',', '')
            return int(result)
    except Exception as e:
        return str(e)

def send_grc(grc_client:common.GridcoinClientConnection,address:str,amount:float)->Union[str,None]:
    response=grc_client.send_tx(destination=address,amount=amount)
    if isinstance(response,dict):
        tx_id=response.get('result')
        if isinstance(tx_id,str):
            return tx_id
    return None
def get_address_balance(address:str)->int:
    html_response=''
    try:
        url='https://www.gridcoinstats.eu/API/simpleQuery.php?q=address&v='+address
        # request user's profile page
        response = requests.get(url)
        html_response = response.content.decode()
        html_response=html_response.replace('\n','')

        # find user credit total
        if html_response.strip()=='':
            return 0
        if 'INVALID ADDRESS' in html_response.upper():
            return 0
        match = re.search("\d*", html_response, flags=re.MULTILINE|re.IGNORECASE)
        if match:
            #print('match is ' + match.group(2))
            result = match.string
            return int(float(result))
    except Exception as e:
        logging.error('Error fetching address balance {} {}. HTML response is {}'.format(address,e,html_response))
        return 0
    return 0
def make_required_credits_html(redis:redis.Redis, project_list:List[str]):
    return_value=''
    for project in project_list:
        standardized_url=common.standardize_project_url(project)
        return_value=return_value+'<li>{}</li>'.format(project)
    return return_value

def get_balance(grc_client:common.GridcoinClientConnection)->int:
    """
    Get balance of wallet, return it as int.
    :param grc_client:
    :return:
    """
    balance_response=grc_client.run_command('getbalance',['*'])
    if isinstance(balance_response,dict):
        balance=balance_response.get('result')
        if isinstance(balance,float):
            return int(balance)
    return 0
@app.route('/about_faucet',methods=['GET'])
def about():
    return render_template('about.html')
@app.route('/',methods=['GET','POST'])
@app.route('/faucet',methods=['GET','POST'])
def faucet():
    try:
        import redis
        pool = redis.ConnectionPool(host='localhost', port=6379, db=0,decode_responses=True)
        redis = redis.Redis(connection_pool=pool)

        # connect to GRC wallet
        grc_rpc_user = config.gridcoin_rpc_user
        grc_rpc_password = config.gridcoin_rpc_password
        grc_rpc_port = config.gridcoin_rpc_port
        grc_client = common.GridcoinClientConnection(rpc_user=grc_rpc_user, rpc_port=grc_rpc_port,
                                                     rpc_password=grc_rpc_password)

        balance = get_balance(grc_client)
        balance_warning = ''
        if balance < 100 and not config.SKIP_LOW_BALANCE_CHECK:
            balance_warning = "Faucet is low on funds, you can't use the faucet right now :("
        # Get global vars for index.html to pull
        total_dispensed=redis.get('total_dispensed')
        total_grc_dispensed=redis.get('total_grc_dispensed')
        app.config['TOTAL_DISPENSED']=str(total_dispensed)
        app.config['TOTAL_GRC_DISPENSED'] = str(total_grc_dispensed)

        required_credits_html=make_required_credits_html(redis, config.project_urls)
    except Exception as e:
        logging.error('Error loading server {}'.format(e))
        return render_template('error.html')
    if request.method == 'POST': # if user has submitted a faucet request
        if not config.SKIP_CAPTCHA:
            if not hcaptcha.verify():
                return render_template('index.html',
                                       ERROR="ERROR: CAPTCHA NOT COMPLETED",
                                       BALANCE=balance,
                                       BALANCE_WARNING=balance_warning, REQUIRED_CREDITS=required_credits_html,
                                       FAUCETADDRESS=config.faucet_donation_address)
        profile_url = common.sanitize_url(request.form.get('profileurl'))
        grc_address = common.sanitize_address(request.form.get('grcaddress'))
        standardized_project_url=common.standardize_project_url(profile_url)
        logging.info('Faucet request: {} {} {}'.format(profile_url,grc_address,standardized_project_url))
        uid=common.uid_from_url(profile_url)
        # perform local checks for username/address eligibility
        if not valid_grc_address(grc_address):
            logging.info('Request declined invalid GRC address')
            return render_template('index.html', ERROR="ERROR: INVALID GRC ADDRESS",BALANCE=balance,BALANCE_WARNING=balance_warning,REQUIRED_CREDITS=required_credits_html,FAUCETADDRESS=config.faucet_donation_address)
        if not valid_profile_url(profile_url):
            logging.info('Request declined invalid profile address')
            return render_template('index.html', ERROR="ERROR: INVALID PROFILE ADDRESS, SEE BELOW FOR EXPECTED FORMAT",BALANCE=balance,BALANCE_WARNING=balance_warning,REQUIRED_CREDITS=required_credits_html,FAUCETADDRESS=config.faucet_donation_address)
        if not uid:
            logging.info('Request declined unable to determine UID')
            return render_template('index.html',
                                   ERROR="ERROR: Unable to determine userID, are you sure profile url is in correct format?",
                                   BALANCE=balance, BALANCE_WARNING=balance_warning,
                                   REQUIRED_CREDITS=required_credits_html, FAUCETADDRESS=config.faucet_donation_address)
        if not config.SKIP_UID_CHECK:
            if common.is_uid_banned(redis=redis,uid=uid,standardized_project_url=standardized_project_url):
                logging.info('Request declined UID banned')
                return render_template('index.html', ERROR="ERROR: You have already used the faucet or already have a beacon tied to your CPID, the faucet can only be used once",BALANCE=balance,BALANCE_WARNING=balance_warning,REQUIRED_CREDITS=required_credits_html,FAUCETADDRESS=config.faucet_donation_address)
        # check that user has a CPID and that it is not banned
        if not config.SKIP_UID_TRANSLATION:
            cpid=common.uid_to_cpid(redis,uid,standardized_project_url)
        else:
            cpid=None
        if not config.SKIP_BEACON_CHECK:
            if cpid==None:
                logging.info('Request declined, no CPID found for UID {}'.format(uid))
                return render_template('index.html',
                                       ERROR="ERROR: Unable to determine your CPID, probably because your account is < 24 hours old. Please try again later",
                                       BALANCE=balance, BALANCE_WARNING=balance_warning,
                                       REQUIRED_CREDITS=required_credits_html,
                                       FAUCETADDRESS=config.faucet_donation_address)
            else:
                if common.is_cpid_banned(redis,cpid=cpid):
                    logging.info('Request declined CPID banned')
                    return render_template('index.html',
                                           ERROR="ERROR: You have already used the faucet or already have a beacon tied to your CPID, the faucet can only be used once",
                                           BALANCE=balance, BALANCE_WARNING=balance_warning,REQUIRED_CREDITS=required_credits_html,FAUCETADDRESS=config.faucet_donation_address)
        if not config.SKIP_UID_TRANSLATION: # this must come AFTER beacon check as UIDs banned for having beacons aren't in UID database
            if not cpid:
                logging.info('Request declined no stats')
                return render_template('index.html',
                                       ERROR="ERROR: Your stats have not been exported by project yet, OR you have a RAC of <1 please try again in 24 hrs and make sure you have crunched at least one workunit the past two weeks",
                                       BALANCE=balance, BALANCE_WARNING=balance_warning,
                                       REQUIRED_CREDITS=required_credits_html,FAUCETADDRESS=config.faucet_donation_address)
        if not config.SKIP_BALANCE_CHECK:
            address_balance=get_address_balance(address=grc_address)
            if address_balance>3:
                logging.info('Request declined address <3')
                return render_template('index.html',
                                   ERROR="ERROR: You are ineligible to use this faucet because you have enough GRC to start a beacon",
                                   BALANCE=balance, BALANCE_WARNING=balance_warning,REQUIRED_CREDITS=required_credits_html,FAUCETADDRESS=config.faucet_donation_address)

        # fetch user profile from project, verify credit amounts
        if not config.SKIP_CREDIT_CHECK:
            user_json=redis.hget('uid_table_'+standardized_project_url,uid)
            if not user_json:
                logging.info('Request declined cant find user credit')
                return render_template('index.html',
                                       ERROR="ERROR: Can't find any assigned credit, you must wait 24 hours for projects to export your credit and have a 'recent average credit' above 1",
                                       BALANCE=balance, BALANCE_WARNING=balance_warning,
                                       REQUIRED_CREDITS=required_credits_html,
                                       FAUCETADDRESS=config.faucet_donation_address)
            if user_json==[None]:
                logging.info('Request declined cant find user credit 2')
                return render_template('index.html',
                                       ERROR="ERROR: Can't find any assigned credit, you must wait 24 hours for projects to export your credit and have a 'recent average credit' above 1",
                                       BALANCE=balance, BALANCE_WARNING=balance_warning,
                                       REQUIRED_CREDITS=required_credits_html,
                                       FAUCETADDRESS=config.faucet_donation_address)
            user = common.json_to_dict(user_json)
            mag_per_rac=redis.get(standardized_project_url + '_rac_mag_ratio')
            if not mag_per_rac:
                logging.info('Request declined no mag_per_rac')
                return render_template('index.html',
                                       ERROR="ERROR: Error fetching project stats please try again later",
                                       BALANCE=balance, BALANCE_WARNING=balance_warning,
                                       REQUIRED_CREDITS=required_credits_html,
                                       FAUCETADDRESS=config.faucet_donation_address)
            credits_result=common.user_above_minimum(user=user,mag_per_rac=float(mag_per_rac),padding=config.padding,faucet_amount=config.faucet_grc_amount)
            if isinstance(credits_result,float):
                logging.info('Request declined not enough credit. Credit_result is {}'.format(credits_result))
                return render_template('index.html',
                                       ERROR="ERROR: Your current crunching would have earned you approx {:.2f} GRC, you must wait until it is over {}. Try again later :)".format(credits_result,config.faucet_grc_amount),
                                       BALANCE=balance, BALANCE_WARNING=balance_warning,
                                       REQUIRED_CREDITS=required_credits_html,
                                       FAUCETADDRESS=config.faucet_donation_address)
        if not config.SKIP_ADDRESS_VERIFICATION:
            credits=''
            if 'ESCATTER11' in profile_url.upper():
                credits=get_credit_nfs(profile_url,grc_address)
            elif 'WORLDCOMMUNITYGRID' in profile_url.upper():
                credits=get_credit_wcg(profile_url,grc_address)
            if isinstance(credits,str):
                logging.info('Request declined error getting profile url: {}'.format(credits))
                logging.error("Error getting profile URL {} : {}".format(profile_url,credits))
                return render_template('index.html',
                                       ERROR="ERROR: Error fetching profile page or parsing url. Make sure you changed your username to your GRC address",
                                       BALANCE=balance, BALANCE_WARNING=balance_warning,
                                       REQUIRED_CREDITS=required_credits_html,
                                       FAUCETADDRESS=config.faucet_donation_address)
            if not credits:
                if isinstance(credits, str):
                    logging.info('Request declined error getting profile url: {}'.format(credits))
                    logging.error("Error getting profile URL {} : {}".format(profile_url, credits))
                return render_template('index.html', ERROR="ERROR: Error fetching profile page or parsing url. Make sure you changed your username to your GRC address",BALANCE=balance,BALANCE_WARNING=balance_warning,REQUIRED_CREDITS=required_credits_html,FAUCETADDRESS=config.faucet_donation_address)
        balance = get_balance(grc_client)
        if balance>10 or config.SKIP_LOW_BALANCE_CHECK:
            if not config.SKIP_BANNING:
                common.ban_uid(redis=redis,uid=uid,standardized_project_url=standardized_project_url)
                common.ban_cpid(redis=redis,cpid=cpid)
            try:
                logging.info('Preparing to award user')
                # send tx
                tx_id=send_grc(grc_client=grc_client,address=grc_address, amount=config.faucet_grc_amount)

                # update stats
                total_dispensed = redis.get('total_dispensed')
                if not total_dispensed:
                    redis.mset({'total_dispensed':1})
                else:
                    redis.mset({'total_dispensed': float(total_dispensed)+1})

                total_grc_dispensed=redis.get('total_grc_dispensed')
                if not total_grc_dispensed:
                    redis.mset({'total_grc_dispensed':config.faucet_grc_amount})
                else:
                    redis.mset({'total_grc_dispensed': float(total_grc_dispensed)+config.faucet_grc_amount})

                # tell user tx successful
                if tx_id:
                    logging.info('Request successful!')
                    return render_template('index.html',
                                           SUCCESS='<p style="color:green;">Transaction successful! You can <a href="https://www.gridcoinstats.eu/tx/{}">view tx on Gridcoinstats</a> in around 1 minute. Remember coins may take up to 10 minutes to fully confirm before they can be used for a beacon.</p>'.format(tx_id),
                                           BALANCE=balance, BALANCE_WARNING=balance_warning,
                                           REQUIRED_CREDITS=required_credits_html,
                                           FAUCETADDRESS=config.faucet_donation_address)
                else:
                    logging.error('No txid returned?')
            except Exception as e:
                logging.error('Error sending {} grc to {}: {}'.format(config.faucet_grc_amount,grc_address,e))
    else:
        return render_template('index.html',BALANCE=balance,BALANCE_WARNING=balance_warning,REQUIRED_CREDITS=required_credits_html,FAUCETADDRESS=config.faucet_donation_address)
def wait_till_synced():
    while True:
        try:
            # connect to GRC wallet
            grc_rpc_user = config.gridcoin_rpc_user
            grc_rpc_password = config.gridcoin_rpc_password
            grc_rpc_port = config.gridcoin_rpc_port
            grc_client = common.GridcoinClientConnection(rpc_user=grc_rpc_user, rpc_port=grc_rpc_port,
                                                         rpc_password=grc_rpc_password)
            common.wait_till_synced(grc_client=grc_client)
            return
        except Exception as e:
            logging.error("Error connecting to grc client at server startup {}".format(e))
        sleep(1)
if __name__=="__main__":
    wait_till_synced() # Wait till GRC client is up and synced
    app.run()