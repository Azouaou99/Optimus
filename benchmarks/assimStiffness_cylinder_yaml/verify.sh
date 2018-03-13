#!/bin/bash

if [ $# == "1" ]; then
        SOFA_EXEC=$1
else
        SOFA_EXEC=runSofa
fi
echo "Using SOFA executable: " $SOFA_EXEC

numItSDA=100
goScene=AppliedForces_GenObs_bench.py
sdaScene=AppliedForces_SDA_bench.py
yamlConfig=cyl10_appliedGravity_bench.yml
compareScript=../helper/compareData.py

#==============================================================

numItObs=$[$numItSDA+1]

rm -rf obs_testing
mkdir -p obs_testing

rm -rf roukf_testing
mkdir -p roukf_testing

echo "Generating observations..."
$SOFA_EXEC -g batch -n $numItObs $goScene --argv $yamlConfig  &> genObsOut
echo "... done"

echo "Running data assimilation..."
$SOFA_EXEC -g batch -n $numItSDA $sdaScene --argv $yamlConfig &> sdaOut
echo "... done"

echo "Comparing state w.r.t. benchmark:"
python $compareScript roukf_bench/state.txt roukf_testing/state.txt $numItSDA

echo "Comparing variance w.r.t. benchmark:"
python $compareScript roukf_bench/variance.txt roukf_testing/variance.txt $numItSDA

echo "Comparing covariance w.r.t. benchmark:"
python $compareScript roukf_bench/covariance.txt roukf_testing/covariance.txt $numItSDA