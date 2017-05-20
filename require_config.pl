#!/usr/bin/perl -w
use JSON;

my $HPC_CHIP;                                                                                                                                                                        
our $BGICGA;
BEGIN {
        die "Please specify environment variable HPC_CHIP_HOME as the home of HPC_CHIP pipeline.\n" if (!exists $ENV{"HPC_CHIP_HOME"});
        $HPC_CHIP = $ENV{"HPC_CHIP_HOME"};
        die "Please specify environment variable BGICGA_HOME as the home of bgicg annotation pipeline.\n" if (!exists $ENV{"BGICGA_HOME"});
        $BGICGA = $ENV{"BGICGA_HOME"};
}

our %config;
require shift;
my $json = encode_json \%config;
print $json;
