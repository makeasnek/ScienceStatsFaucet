from typing import List,Union,Dict,Tuple
import json,gzip
import config
import redis,common,os,logging,xmltodict
logging.basicConfig(filename='server.log', level=logging.ERROR)
def get_project_mag_ratios(grc_client: common.GridcoinClientConnection, lookback_period: int = 30) -> Dict[
    str, float]:
    """
    :param grc_client:
    :param lookback_period: number of superblocks to look back to determine average
    :return: Dictionary w/ key as project URL and value as project mag ratio (mag per unit of RAC)
    """
    projects = {}
    return_dict = {}
    mag_per_project = 0
    command_result= grc_client.run_command('superblocks', [30, True])
    for i in range(0, lookback_period):
        superblock=command_result['result'][i]
        if i == 0:
            total_magnitude = superblock['total_magnitude']
            total_projects = superblock['total_projects']
            mag_per_project = total_magnitude / total_projects
        for project_name, project_stats in superblock['Contract Contents']['projects'].items():
            if project_name not in projects:
                if i==0:
                    projects[project_name] = []
                else:
                    continue # skip projects which are on greylist
            projects[project_name].append(project_stats['rac'])
    for project_name, project_racs in projects.items():
        average_rac = sum(project_racs) / len(project_racs)
        project_url = grc_client.project_name_to_url(project_name)
        return_dict[project_url] = mag_per_project / average_rac
    return return_dict
def update_project_stats(data_storage_dir:str=config.data_storage_dir,project_urls:List[str]=None):
    import urllib.request
    if not project_urls:
        project_urls=config.project_urls
    # downloaded updated stats file
    for project_url in project_urls:
        user_stats_file=os.path.join(project_url,'stats','user.gz')
        standardized_url=common.standardize_project_url(project_url)
        temp_stats_file_dest=os.path.join(data_storage_dir+standardized_url+'_user_new.gz')
        final_stats_file_dest=os.path.join(data_storage_dir,standardized_url+'_user.gz')
        try:
            urllib.request.urlretrieve(user_stats_file, temp_stats_file_dest)
        except Exception as e:
            logging.error('Error downloading project stats: {} {}'.format(user_stats_file,e))
        else:
            if os.path.exists(final_stats_file_dest):
                os.remove(final_stats_file_dest)
            os.rename(temp_stats_file_dest,final_stats_file_dest)
def ban_beaconed_users(redis:redis.Redis,project_urls:List[str],data_storage_dir:str=config.data_storage_dir,grc_client=common.GridcoinClientConnection):
    """
    Reads in stats from project(s), creates UID->CPID lookup tables, bans CPIDs and UIDs associated with beacons
    :param redis:
    :param project_urls:
    :param data_storage_dir:
    :param grc_client:
    :return:
    """
    def should_be_banned(cpid:str,grc_client:common.GridcoinClientConnection)->bool:
        """
        Given CPID and beacon status, return True if user has an active or pending beacon
        :param cpid:
        :param grc_client:
        :return:
        """
        beacon_status = grc_client.run_command('beaconstatus', [cpid])
        if 'result' in beacon_status:
            if 'active' in beacon_status['result']:
                if len(beacon_status['result']['active'])>0:
                    #print('banning cpid {} {}'.format(cpid,beacon_status))
                    return True
            if 'pending' in beacon_status['result']:
                if len(beacon_status['result']['pending']) > 0:
                    return True
        return False
    if not project_urls:
        project_urls=config.project_urls
    # import stats into redis db
    for project_url in project_urls:
        uids_to_ban=set()
        cpids_to_ban=set()
        mapping_table={}
        standardized_url = common.standardize_project_url(project_url)
        final_stats_file_dest = os.path.join(data_storage_dir, standardized_url + '_user.gz')
        if not os.path.exists(final_stats_file_dest): # no stats exist for project
            continue
        with gzip.open(final_stats_file_dest, 'rt') as file:
            user_data = file.read()
        try:
            user_dict=xmltodict.parse(user_data)
        except Exception as e:
            logging.error("Error parsing file: {} {}".format(final_stats_file_dest,e))
            continue
        for user in user_dict.get('users',{}).get('user',{}):
            uid=user['id']
            cpid=user['cpid']
            rac=user.get('expavg_credit',0)
            if should_be_banned(cpid,grc_client) and str(uid)!='3710112':
                uids_to_ban.add(uid)
                cpids_to_ban.add(cpid)
            else:
                if float(rac)>1:
                    mapping_table[uid]=cpid
        common.ban_uid(redis,uids_to_ban,standardized_url)
        common.ban_cpid(redis,cpids_to_ban)
        result=redis.hset("uid_table_"+standardized_url, mapping=mapping_table)

if __name__=="__main__":
    grc_rpc_user = config.gridcoin_rpc_user
    grc_rpc_password = config.gridcoin_rpc_password
    grc_rpc_port = config.gridcoin_rpc_port
    faucet_grc_amount=config.faucet_grc_amount
    # connect to redis
    pool = redis.ConnectionPool(host='localhost', port=6379, db=0,decode_responses=True)
    redis = redis.Redis(connection_pool=pool)
    # clear existing db, useful for debugging
    # redis.flushdb()

    # connect to wallet
    grc_client = common.GridcoinClientConnection(rpc_user=grc_rpc_user, rpc_port=grc_rpc_port,
                                                 rpc_password=grc_rpc_password)
    # download project stats, ban users w/ beacons
    update_project_stats(config.data_storage_dir,config.project_urls)
    ban_beaconed_users(redis,config.project_urls,config.data_storage_dir,grc_client=grc_client)

    # figure out required credits
    lookback_period=30
    mag_ratios = get_project_mag_ratios(grc_client,lookback_period)
    required_mag=faucet_grc_amount*4
    credit_requirements={}
    for project_url,mag_per_unit_of_rac in mag_ratios.items():
        standardized_url=common.standardize_project_url(project_url)
        required_rac=required_mag/mag_per_unit_of_rac
        required_credits_to_reach_rac=(required_rac*7)
        final_requirement=int(required_credits_to_reach_rac+(required_credits_to_reach_rac*.20))
        redis.set(standardized_url+'_required_credits',final_requirement)
