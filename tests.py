import common
import main,redis
# Various tests to make sure any future changes don't break core functionality. Also see tests_network.py

# GRC address checker
assert main.valid_grc_address('SDeLtAzzaNkvom9HzVgdHHGToEjZ7sYipp')==True
assert main.valid_grc_address('SDeLtAzzaNkvom9HzVgdHHGToEjZ7sYip')==False
assert main.valid_grc_address('')==False

# common UID & CPID functions
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
redis_connection = redis.Redis(connection_pool=pool)
standardized_url=common.standardize_project_url('https://escatter11.fullerton.edu/nfs/')
common.ban_uid(redis=redis_connection,uid='testing',standardized_project_url=standardized_url)
assert common.is_uid_banned(redis=redis_connection,uid='testing',standardized_project_url=standardized_url)
common.unban_uid(redis=redis_connection,uid='testing',standardized_project_url=standardized_url)
assert not common.is_uid_banned(redis=redis_connection,uid='testing',standardized_project_url=standardized_url)
#
common.ban_cpid(redis=redis_connection,cpid='testing')
assert common.is_cpid_banned(redis=redis_connection,cpid='testing')
common.unban_cpid(redis=redis_connection,cpid='testing')
assert not common.is_cpid_banned(redis=redis_connection,cpid='testing')
standardized_url=common.standardize_project_url('https://escatter11.fullerton.edu/nfs/')
assert not common.uid_to_cpid(redis=redis_connection,uid='THISUIDDOESNOTEXIST',standardized_project_url=standardized_url)

# Sanitizing code
assert common.sanitize_url("<a href='https://escatter11.fullerton.edu/nfs/show_user.php?userid=21405'\n\n>")=='ahref=https://escatter11.fullerton.edu/nfs/show_user.php?userid=21405'
assert common.sanitize_address("<a href='https://escatter11.fullerton.edu/nfs/show_user.php?userid=21405'\n\n>")=='ahrefhttpsescatter11fullertonedunfsshowuserphpuserid2145'

# URL address checker
assert main.valid_profile_url('ESCATTER11.FULLERTON.EDU/NFS/SHOW_USER.PHP?USERID=21405')==True
assert main.valid_profile_url('https://escatter11.fullerton.edu/nfs/show_user.php?userid=21405')==True
assert main.valid_profile_url('https://www.worldcommunitygrid.org/stat/viewMemberInfo.do?userName=ericinboston')==True
assert main.valid_profile_url('')==False
assert main.valid_profile_url('google.com')==False

# URL standardizer
assert 'ESCATTER11.FULLERTON.EDUNFS'==common.standardize_project_url('https://escatter11.fullerton.edu/nfs/')
assert 'ESCATTER11.FULLERTON.EDUNFS'==common.standardize_project_url('https://escatter11.fullerton.edu/nfs/show_user.php?userid=21405')

# JSON encoding/decoding
test_dict={
    'A':'A',
    'B':1,
    'C':['A','B'],
    'D':True,
    'E':False,
    'F':2.144
}
my_json=common.dict_to_json(test_dict)
assert my_json=='{"A": "A", "B": 1, "C": ["A", "B"], "D": true, "E": false, "F": 2.144}'
dict_output=common.json_to_dict(my_json)
assert test_dict==dict_output