# Utility to debug certain functions, figure out why faucet is rejecting a particular request
import main
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


def menu():
    print('1. Check Profile Page')
    answer=input('')
    if answer=='1':
        check_profile()
if __name__=='__main__':
    menu()