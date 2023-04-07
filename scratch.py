import config
import daily,redis,common
import main

grc_rpc_user = config.gridcoin_rpc_user
grc_rpc_password = config.gridcoin_rpc_password
grc_rpc_port = config.gridcoin_rpc_port
grc_client=common.GridcoinClientConnection(rpc_user=grc_rpc_user,rpc_port=grc_rpc_port,rpc_password=grc_rpc_password)

pool = redis.ConnectionPool(host='localhost', port=6379, db=0,decode_responses=True)
redis = redis.Redis(connection_pool=pool)
mag_ratios=daily.get_project_mag_ratios(grc_client,30)
required_mag=config.faucet_grc_amount*4
for project_url, mag_per_unit_of_rac in mag_ratios.items():
    standardized_url = common.standardize_project_url(project_url)
    get_all = redis.hgetall('uid_table_' + standardized_url)
    print('Found {} users for {}'.format(len(get_all),standardized_url))
    # ORIGINAL CALCULATION METHOD:
    required_rac = required_mag / mag_per_unit_of_rac
    required_credits_to_reach_rac = (required_rac * 14)
    final_requirement = int(required_credits_to_reach_rac + (required_credits_to_reach_rac * .20))
    for uid,json_dict in get_all.items():
        user_dict=common.json_to_dict(json_dict)
        #print('Original guess was {}, required RAC is {}'.format(final_requirement,required_rac))
        print('UID: '+uid)
        common.user_above_minimum(user_dict,mag_per_unit_of_rac,.15,2)
    stop=input('')


