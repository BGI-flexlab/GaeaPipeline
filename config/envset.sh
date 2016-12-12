#### set GAEA_HOME
export GAEA_HOME=/ifs4/ISDC_BD/GaeaProject/software/GaeaPipeline
export PATH=$GAEA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$GAEA_HOME/lib:$LD_LIBRARY_PATH
export PYTHONPATH=$GAEA_HOME/bin:$PYTHONPATH

## Submit workflow
Gaea.py -w ./ -d /user/yourname -s sample.list -c conf.cfg -j testGaea
