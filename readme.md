# ScienceStats Gridcoin "Proof of Work" Faucet

This is a repo to contain the ScienceStats Gridcoin "Proof of Work" Faucet.

The site is written in Python and uses a redis server to store information. Why Redis? Because learning SQL seemed hard.
## Faucet goal
Require a set amount of "work" to use faucet, such that users have no incentive to use faucet more than once. This faucet is best used to help onboard users who need their first few GRC to setup a beacon.

Other faucets have trouble staying sustainably funded as they hand out coins to whoever asks. This faucet actually makes them work for it.

## Faucet features
 - Requires user to earn a set amount of credit at BOINC project(s) in order to use faucet
 - This amount is dynamically calculated based on how much credit a user would need to _normally_ earn the faucet's payout amount via solo or pool crunching
 - Supports multiple projects with room for expansion
 - Maps user IDs at projects to CPIDs and bans both after a single use
 - Integrates directly with a Gridcoin wallet to send transactions

### Customization
 - Enable/disable hcaptcha
 - Enable/disable banning UIDs and CPIDs after single-use
 - Add your own favourite BOINC projects as required work
 - Enable/disable requiring work at all, you can just turn this into a regular faucet

Extendability: One could conceivably extend this faucet to distribute other coins such as Etica. All that would be needed is to:
 - Establish an exchange rate between GRC and chosen coin
 - Write code to send the tx via that coin's wallet or via RPC to remote node like Metamask does.

## To run your own faucet
 - You must have localhost access to a Gridcoin wallet's RPC port and access to a redis server
 - Requires python 3.6 or higher and packages listed in requirements.txt
 - Download this repo
 - Copy config_template.py to config.py, modify to suit your use case
 - Edit templates/index.html and templates/about.html to your liking. Note the google analytics tag near bottom and hcaptcha.
 - Run daily.py for the first time to build the database
 - Create a cron job to run daily.py every 24 hours to download stats from BOINC project websites
   - Example cron entry: 
   - Line 1: SHELL=/bin/bash
   - Line2: 0 1 * * * source /var/www/html/ScienceStatsFaucet/your_site_environment/bin/activate && /var/www/html/ScienceStatsFaucet/your_site_environment/bin/python3.10 /var/www/html/ScienceStatsFaucet/daily.py 2>1 >> /wherever/you/want/log.txt
 - The stats download is rather CPU intensive for you and bandwidth intensive for the BOINC projects you support, so please be nice and don't do this more than once a day
 - Run main.py

### System requirements
Testing this on an Ubuntu machine got me these basic requirements:

Memory: suggested absolute minimum 2GB
 - gridcoin (GUI wallet) 800MB
 - daily script when running: 50MB
 - main script when running: 25MB
 - redis: 10MB
 - This memory usage is just stats from NFS@Home, WCG is not included in them.

Disk: suggested minimum 6.5GB 
 - Gridcoin (GUI wallet) 5.5GB
 - Redis <100MB
 - Project stats varies by project, NFS@Home was <5MB

## Legal & License
 - Released under GPLv3 terms available in license.txt file. 
 - I ask that you link back to the sciencestats website, but it is not legally required.
 - This code is released without any warranty whatsoever. You'll probably lose all the coins you put into the faucet, don't blame me.