# These tests require network access and result in requests to BOINC project servers, so should be run seperately from
# automated tests

import main

# PROFILE CHECK. Note these will fail if random user we selected changes their username
assert isinstance(main.get_credit_nfs('https://escatter11.fullerton.edu/nfs/show_user.php?userid=760','ChertseyAl'),int)
assert isinstance(main.get_credit_amicable('https://sech.me/boinc/Amicable/show_user.php?userid=2167','modesti'),int)
wcg_credit=main.get_credit_wcg('https://worldcommunitygrid.org/boinc/show_user.php?userid=1156028','S5CSzXD3SkTA9xGGpeBtoNJpyryACBR9RD')
assert wcg_credit==None

# Address check. Note this will fail if the address balance is actually 0
balance=main.get_address_balance('SK7WASoXZFQrQLwTmabkS3Co8RUq6UevDU')
assert balance>0