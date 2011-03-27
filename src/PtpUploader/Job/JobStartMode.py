class JobStartMode:
	Automatic    = 0
	Manual       = 1
	
	'''
	If this is set then:
	- there is no duplicate checking
	- there is no adult tag checking
	- series is not rejected
	- user specified container overrides the one returned by MediaInfo (even if they are different)
	- user specified codec overrides the one returned by MediaInfo (even if they are different)
	- user specified resolution overrides the one returned by MediaInfo (even if they are different)
	'''
	ManualForced = 2