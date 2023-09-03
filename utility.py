# Utility to debug certain functions, figure out why faucet is rejecting a particular request
import common
import main
import redis
def check_profile():
    answer=input('Enter profile url')
    grc_address=input('Enter GRC address')
    credits=None
    if 'ESCATTER11' in answer.upper():
        credits = main.get_credit_nfs(answer, grc_address)
    elif 'WORLDCOMMUNITYGRID' in answer.upper():
        credits = main.get_credit_wcg(answer, grc_address)
    if credits:
        print('Address matches profile')
        print('Returnvalue is {}'.format(credits))



def check_cpid():
    import redis
    print('Enter user profile page')
    answer=input('')
    pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)
    redis = redis.Redis(connection_pool=pool)
    uid=common.uid_from_url(answer)
    standardized_project_url = common.standardize_project_url(answer)
    if common.is_uid_banned(redis=redis, uid=uid, standardized_project_url=standardized_project_url):
        print('Request declined UID banned')
    cpid = common.uid_to_cpid(redis, uid, standardized_project_url)
    if not cpid:
        print('No cpid found')
        return
    if common.is_cpid_banned(redis, cpid=cpid):
        print('Request declined CPID banned')
def unban_user():
    import redis
    answer=input('Enter user profile')
    pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)
    redis = redis.Redis(connection_pool=pool)
    uid=common.uid_from_url(answer)
    standardized_project_url = common.standardize_project_url(answer)
    cpid = common.uid_to_cpid(redis, uid, standardized_project_url)
    common.unban_uid(redis,uid,standardized_project_url)
    if cpid:
        common.unban_cpid(redis,cpid)
def menu():
    print('1. Check Profile Page')
    print('2. Check if user profile has beacon')
    print('3. Unban user')
    answer=input('')
    if answer=='1':
        check_profile()
    elif answer=='2':
        check_cpid()
    elif answer=='3':
        unban_user()
if __name__=='__main__':
    menu()