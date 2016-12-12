#!/usr/bin/perl -w
use strict;

my $err_file = shift;
	
open ERR, "$err_file" or die "$!";
while(<ERR>)
{
	chomp;
	if(/fail/i)
	{
		close ERR;
		exit -1;
	}
}
close ERR;
exit 0;
