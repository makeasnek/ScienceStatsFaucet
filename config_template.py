from typing import List,Dict,Tuple
gridcoin_rpc_user:str='username_here'
gridcoin_rpc_password:str='password_here'
gridcoin_rpc_port:str='port_here'
faucet_grc_amount:float=1.5
data_storage_dir:str='/opt/faucet' # where to store data for faucet, should not be accessible by web users
faucet_donation_address='' # if you want to solicit donations for the faucet, put in your address here
padding:float=.15 # Faucet calculate how many credits user would need to earn X GRC solo crunching. This is the % extra we tack on to make faucet more expensive. So .15=15%
# hcaptcha stuff
HCAPTCHA_SITE_KEY = ''
HCAPTCHA_SECRET_KEY = ''
HCAPTCHA_ENABLED:bool=True

# Supported projects
# To add a project, you must modify each of the below variables and create custom functions for them.
# See get_credit_nfs in main.py for example, and modify code which references it
project_urls:List[str]=['https://escatter11.fullerton.edu/nfs/','https://www.worldcommunitygrid.org/boinc/']
valid_profile_regexes = [
        'escatter11.fullerton.edu/nfs/show_user.php\?userid=\d*',
    'worldcommunitygrid.org/stat/viewMemberInfo.do?userName=\w*'
    ]

# Dev options. Various options to make testing easier
SKIP_CAPTCHA:bool=False # Skip verifying captcha
SKIP_UID_CHECK:bool=False # Skip checking if UID is banned
SKIP_UID_TRANSLATION:bool=False # Skip checking for CPID to see if it's banned
SKIP_BEACON_CHECK:bool=False # Skip checking if CPID is already beaconed
SKIP_BALANCE_CHECK:bool=False # Skip checking if destination address already has a balance
SKIP_LOW_BALANCE_CHECK:bool=False # Skip disabling faucet if balance is too low
SKIP_BANNING:bool=False # Skip banning users after first use
SKIP_CREDIT_CHECK:bool=False # hand out GRC regardless of user credit amount
