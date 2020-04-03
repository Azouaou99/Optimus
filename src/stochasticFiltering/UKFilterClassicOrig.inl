#ifndef UKFilterClassicOrig_INL
#define UKFilterClassicOrig_INL

#include "UKFilterClassicOrig.h"
#include <iostream>
#include <fstream>

namespace sofa
{
namespace component
{
namespace stochastic
{

template <class FilterType>
UKFilterClassicOrig<FilterType>::UKFilterClassicOrig()
    : Inherit()
    , d_exportPrefix( initData(&d_exportPrefix, "exportPrefix", "prefix for storing various quantities into files"))
    , d_filenameCov( initData(&d_filenameCov, "filenameCov", "output file name"))
    , d_filenameInn( initData(&d_filenameInn, "filenameInn", "output file name"))
    , d_filenameFinalState( initData(&d_filenameFinalState, "filenameFinalState", "output file name"))
    , d_state( initData(&d_state, "state", "actual expected value of reduced state (parameters) estimated by the filter" ) )
    , d_variance( initData(&d_variance, "variance", "actual variance  of reduced state (parameters) estimated by the filter" ) )
    , d_covariance( initData(&d_covariance, "covariance", "actual co-variance  of reduced state (parameters) estimated by the filter" ) )
    , d_innovation( initData(&d_innovation, "innovation", "innovation value computed by the filter" ) )
    , d_draw(initData(&d_draw, false, "draw","Activation of draw"))
    , d_radius_draw( initData(&d_radius_draw, (double) 0.005, "radiusDraw", "radius of the spheres") )
    , d_MOnodes_draw( initData(&d_MOnodes_draw,(double) 1.0, "MOnodesDraw", "nodes of the mechanical object") )

{

}

template <class FilterType>
void UKFilterClassicOrig<FilterType>::computePerturbedStates()
{
    EVectorX xCol(stateSize);
    int currentPointID = 0;

    for (size_t i = 0; i < sigmaPointsNum; i++) {
        xCol = matXi.col(i);
        stateWrappers[0]->transformState(xCol, mechParams, &currentPointID);
        m_sigmaPointObservationIndexes[i] = currentPointID;
        matXi.col(i) = xCol;
    }
}

template <class FilterType>
void UKFilterClassicOrig<FilterType>::computePrediction()
{
    hasObs = observationManager->hasObservation(this->actualTime);
    if (hasObs) {
        // std::cout<<"\n HAS OBS: =" << hasObs << " COMPUTE PREDICTION" << std::endl;
        PRNS("Computing prediction, T= " << this->actualTime  << " ======");
        //std::cout << "Computing prediction, T= " << this->actualTime  << " ======" << std::endl;
        /// Computes background error variance Cholesky factorization.
        Eigen::LLT<EMatrixX> lltU(stateCovar);
        EMatrixX matPsqrt = lltU.matrixL();
        //std::cout << "matPsqrt: " << matPsqrt << std::endl;

        ///// Computes Square Root with SVD --- Raffaella's modification instead of Cholesky factorization
        //EMatrixX matPsqrt(stateSize,stateSize);
        //sqrtMat(stateCovar, matPsqrt);
        //// end of Raffaella's modification

        stateExp.fill(FilterType(0.0));
        stateExp = masterStateWrapper->getState();

        /// Computes X_{n}^{(i)-} sigma points
        for (size_t i = 0; i < sigmaPointsNum; i++) {
            matXi.col(i) = stateExp + matPsqrt * matI.row(i).transpose();
        }

        //std::cout << "matXi: " << matXi << std::endl;
        /// Propagate sigma points
        genMatXi=matXi.transpose();
        computePerturbedStates();
        //std::cout << "matXi: " << matXi << std::endl;

        /// Compute Predicted Mean
        stateExp.fill(FilterType(0.0));
        for (size_t i = 0; i < sigmaPointsNum; i++) {
            stateExp += matXi.col(i) * vecAlpha(i);
        }

        /// Compute Predicted Covariance
        stateCovar.setZero();
        EMatrixX matXiTrans= matXi.transpose();
        EMatrixX centeredPxx = matXiTrans.rowwise() - matXiTrans.colwise().mean();
        EMatrixX weightedCenteredPxx = centeredPxx.array().colwise() * vecAlphaVar.array();
        EMatrixX covPxx = (centeredPxx.adjoint() * weightedCenteredPxx);
        //EMatrixX covPxx = (centeredPxx.adjoint() * centeredPxx) / double(centeredPxx.rows() )
        stateCovar = covPxx + modelCovar;
        for (size_t i = 0; i < (size_t)stateCovar.rows(); i++) {
            diagStateCov(i)=stateCovar(i,i);
        }

        masterStateWrapper->setState(stateExp, mechParams);

    }else{
        // std::cout<<"\n HAS OBS: =" << hasObs << " COMPUTE ONLY PREDICTION" << std::endl;

        ///// --- Raffaella's modification instead of Cholesky factorization
        //// stateExp.fill(FilterType(0.0));
        //// stateExp = masterStateWrapper->getState();
        //// masterStateWrapper->lastApplyOperator(stateExp, mechParams);

        //EMatrixX matPsqrt(stateSize,stateSize);
        //sqrtMat(stateCovar, matPsqrt);
        //// end of Raffaella's modification

        stateExp.fill(FilterType(0.0));
        stateExp = masterStateWrapper->getState();
        Eigen::LLT<EMatrixX> lltU(stateCovar);
        EMatrixX matPsqrt = lltU.matrixL();


        /// Computes X_{n}^{(i)-} sigma points
        for (size_t i = 0; i < sigmaPointsNum; i++) {
            matXi.col(i) = stateExp + matPsqrt * matI.row(i).transpose();
        }

        /// Propagate sigma points
        genMatXi=matXi.transpose();
        computePerturbedStates();

        /// Compute Predicted Mean
        stateExp.fill(FilterType(0.0));
        for (size_t i = 0; i < sigmaPointsNum; i++) {
            stateExp += matXi.col(i) * vecAlpha(i);
        }

        /// Compute Predicted Covariance
        stateCovar.setZero();
        EMatrixX matXiTrans= matXi.transpose();
        EMatrixX centeredPxx = matXiTrans.rowwise() - matXiTrans.colwise().mean();
        EMatrixX weightedCenteredPxx = centeredPxx.array().colwise() * vecAlphaVar.array();
        EMatrixX covPxx = (centeredPxx.adjoint() * weightedCenteredPxx);
        stateCovar = covPxx + modelCovar;
        for (size_t i = 0; i < (size_t)stateCovar.rows(); i++) {
            diagStateCov(i)=stateCovar(i,i);
        }

        //masterStateWrapper->setState(stateExp, mechParams);
        masterStateWrapper->lastApplyOperator(stateExp, mechParams);
        PRNS("PREDICTED STATE X(n+1)+n: \n" << stateExp.transpose());
    }
}

template <class FilterType>
void UKFilterClassicOrig<FilterType>::computeCorrection()
{

    if (hasObs) {
        // std::cout<<"\n HAS OBS: =" << hasObs << " COMPUTE CORRECTION" << std::endl;

        PRNS("======= Computing correction, T= " << this->actualTime << " ======");
        std::cout << "======= Computing correction, T= " << this->actualTime << " ======" << std::endl;

        EVectorX zCol(observationSize);
        matZmodel.resize(observationSize, sigmaPointsNum);
        predObsExp.resize(observationSize);
        predObsExp.fill(FilterType(0.0));

        /// Compute Predicted Observations
        for (size_t i = 0; i < sigmaPointsNum; i++) {
            observationManager->getPredictedObservation(m_sigmaPointObservationIndexes[i],  zCol);
            //std::cout << "zCol: " << zCol << std::endl;
            matZmodel.col(i) = zCol;
            predObsExp = predObsExp + zCol * vecAlpha(i);
        }

        /// Compute State-Observation Cross-Covariance
        EMatrixX matPxz(stateSize, observationSize);
        EMatrixX matPz(observationSize, observationSize);
        EMatrixX pinvmatPz(observationSize, observationSize);


        EMatrixX matXiTrans= matXi.transpose();
        EMatrixX matZItrans = matZmodel.transpose();
        EMatrixX centeredCx = matXiTrans.rowwise() - matXiTrans.colwise().mean();
        EMatrixX centeredCz = matZItrans.rowwise() - matZItrans.colwise().mean();
        //EMatrixX covPxz = (centeredCx.adjoint() * centeredCz) / double(centeredCx.rows() );
        EMatrixX weightedCenteredCz = centeredCz.array().colwise() * vecAlphaVar.array();
        EMatrixX covPxz = (centeredCx.adjoint() * weightedCenteredCz);
        //std::cout << "covPxz: " << covPxz << std::endl;

        /// Compute Observation Covariance
        matPxz=covPxz;
        //EMatrixX covPzz = (centeredCz.adjoint() * centeredCz) / double(centeredCz.rows() );
        EMatrixX covPzz = (centeredCz.adjoint() * weightedCenteredCz);
        matPz = obsCovar + covPzz;
        //std::cout << "matPz: " << matPz << std::endl;

        /// Compute Kalman Gain
        EMatrixX matK(stateSize, observationSize);
        pseudoInverse(matPz, pinvmatPz);
        matK =matPxz*pinvmatPz;

        /// Compute Innovation
        EVectorX innovation(observationSize);
        observationManager->getInnovation(this->actualTime, predObsExp, innovation);
        //std::cout << "Innovation: " << innovation << std::endl;

        /// Compute Final State and Final Covariance
        stateExp = stateExp + matK * innovation;
        //std::cout << "matK: " << matK << std::endl;
        stateCovar = stateCovar - matK*matPxz.transpose();

        for (size_t i = 0; i < (size_t)stateCovar.rows(); i++) {
            diagStateCov(i)=stateCovar(i,i);
        }

        //std::cout << "FINAL STATE X(n+1)+n: " << stateExp.transpose() << std::endl;
        //std::cout << "FINAL COVARIANCE DIAGONAL P(n+1)+n: " << diagStateCov.transpose() << std::endl;
        PRNS("FINAL STATE X(n+1)+n: \n" << stateExp.transpose());
        PRNS("FINAL COVARIANCE DIAGONAL P(n+1)+n:  \n" << diagStateCov.transpose());

        masterStateWrapper->setState(stateExp, mechParams);

        /// Write Some Data for Validation
        helper::WriteAccessor<Data <helper::vector<FilterType> > > stat = d_state;
        helper::WriteAccessor<Data <helper::vector<FilterType> > > var = d_variance;
        helper::WriteAccessor<Data <helper::vector<FilterType> > > covar = d_covariance;
        helper::WriteAccessor<Data <helper::vector<FilterType> > > innov = d_innovation;

        stat.resize(stateSize);
        var.resize(stateSize);
        size_t numCovariances = (stateSize*(stateSize-1))/2;
        covar.resize(numCovariances);
        innov.resize(observationSize);

        size_t gli = 0;
        for (size_t i = 0; i < stateSize; i++) {
            stat[i] = stateExp[i];
            var[i] = stateCovar(i,i);
            for (size_t j = i+1; j < stateSize; j++) {
                covar[gli++] = stateCovar(i,j);
            }
        }
        for (size_t index = 0; index < observationSize; index++) {
            innov[index] = innovation[index];
        }

        //char nstepc[100];
        //sprintf(nstepc, "%04lu", stepNumber);
        //if (! exportPrefix.empty()) {
        //    std::string fileName = exportPrefix + "/covar_" + nstepc + ".txt";
        //    std::ofstream ofs;
        //    ofs.open(fileName.c_str(), std::ofstream::out);
        //    ofs << stateCovar << std::endl;
        //}

        writeValidationPlot(d_filenameInn.getValue(),innovation);
    }
    writeValidationPlot(d_filenameCov.getValue(), diagStateCov);
    writeValidationPlot(d_filenameFinalState.getValue(), stateExp);

}



template <class FilterType>
void UKFilterClassicOrig<FilterType>::init() {
    Inherit::init();
    assert(this->gnode);

    this->gnode->template get<StochasticStateWrapperBaseT<FilterType> >(&stateWrappers, this->getTags(), sofa::core::objectmodel::BaseContext::SearchDown);
    PRNS("found " << stateWrappers.size() << " state wrappers");
    masterStateWrapper=NULL;
    size_t numSlaveWrappers = 0;
    size_t numMasterWrappers = 0;
    numThreads = 0;
    for (size_t i = 0; i < stateWrappers.size(); i++) {
        stateWrappers[i]->setFilterKind(CLASSIC);
        if (stateWrappers[i]->isSlave()) {
            numSlaveWrappers++;
            PRNS("found stochastic state slave wrapper: " << stateWrappers[i]->getName());
        } else {
            masterStateWrapper = stateWrappers[i];
            numMasterWrappers++;
            PRNS("found stochastic state master wrapper: " << masterStateWrapper->getName());
        }
    }

    if (numMasterWrappers != 1) {
        PRNE("Wrong number of master wrappers: " << numMasterWrappers);
        return;
    }

    if (numThreads > 0) {
        PRNS("number of slave wrappers: " << numThreads-1);
        /// slaves + master
    }
    numThreads=numSlaveWrappers+numMasterWrappers;

    this->gnode->get(observationManager, core::objectmodel::BaseContext::SearchDown);
    if (observationManager) {
        PRNS("found observation manager: " << observationManager->getName());
    } else
        PRNE("no observation manager found!");

    /// Init for Write Function
    exportPrefix  = d_exportPrefix.getFullPath();
    PRNS("export prefix: " << exportPrefix)

    this->saveParam = false;
    if (!d_filenameCov.getValue().empty()) {
        std::ofstream paramFile(d_filenameCov.getValue().c_str());
        if (paramFile.is_open()) {
            this->saveParam = true;
            paramFile.close();
        }
    }
    if (!d_filenameInn.getValue().empty()) {
        std::ofstream paramFileInn(d_filenameInn.getValue().c_str());
        if (paramFileInn .is_open()) {
            this->saveParam = true;
            paramFileInn.close();
        }
    }
    if (!d_filenameFinalState.getValue().empty()) {
        std::ofstream paramFileFinalState(d_filenameFinalState.getValue().c_str());
        if (paramFileFinalState .is_open()) {
            this->saveParam = true;
            paramFileFinalState.close();
        }
    }
    m_omega= ((double) rand() / (RAND_MAX));
    //m_omega= 1e-5;


}

template <class FilterType>
void UKFilterClassicOrig<FilterType>::bwdInit() {
    assert(masterStateWrapper);

    stateSize = masterStateWrapper->getStateSize();
    //std::cout<< "[UKF] stateSize " << stateSize << std::endl;
    //PRNS("StateSize " << stateSize);

    /// Initialize Observation's data
    if (!initialiseObservationsAtFirstStep.getValue()) {
        observationSize = this->observationManager->getObservationSize();
        PRNS("Observation size: " << observationSize);
        if (observationSize == 0) {
            PRNE("No observations available, cannot allocate the structures!");
        }
        obsCovar = observationManager->getErrorVariance();
    }


    /// Initialize Model's Error Covariance
    stateCovar = masterStateWrapper->getStateErrorVariance();

    diagStateCov.resize(stateCovar.rows());
    for (size_t i = 0; i < (size_t)stateCovar.rows(); i++) {
        diagStateCov(i)=stateCovar(i,i);
    }
    PRNS(" INIT COVARIANCE DIAGONAL P(n+1)+n:  \n" << diagStateCov.transpose());

    modelCovar = masterStateWrapper->getModelErrorVariance();
    PRNS(" INIT COVARIANCE DIAGONAL P(n+1)+n:  \n" << modelCovar);

    stateExp = masterStateWrapper->getState();

    /// Compute Sigma Points
    switch (this->m_sigmaTopology) {
    case STAR:
        computeStarSigmaPoints(matI);
        break;
    case SIMPLEX:
    default:
        computeSimplexSigmaPoints(matI);
    }

    sigmaPointsNum = matI.rows();
    matXi.resize(stateSize, sigmaPointsNum);
    matXi.setZero();
    genMatXi.resize( sigmaPointsNum,stateSize);
    genMatXi.setZero();

    /// Initialise State Observation Mapping for Sigma Points
    m_sigmaPointObservationIndexes.resize(sigmaPointsNum);
}

template <class FilterType>
void UKFilterClassicOrig<FilterType>::initializeStep(const core::ExecParams* _params, const size_t _step) {
    Inherit::initializeStep(_params, _step);

    if (initialiseObservationsAtFirstStep.getValue()) {
        observationSize = this->observationManager->getObservationSize();
        PRNS("Observation size: " << observationSize);
        if (observationSize == 0) {
            PRNE("No observations available, cannot allocate the structures!");
        }
        obsCovar = observationManager->getErrorVariance();
        initialiseObservationsAtFirstStep.setValue(false);
    }

    for (size_t i = 0; i < stateWrappers.size(); i++)
        stateWrappers[i]->initializeStep(stepNumber);

    observationManager->initializeStep(stepNumber);
}



template <class FilterType>
void UKFilterClassicOrig<FilterType>::updateState() {

    stateSize = masterStateWrapper->getStateSize();
    //std::cout<< "new [UKF] stateSize " << stateSize << std::endl;
    //PRNS("StateSize " << stateSize);

    /// Initialize Model's Error Covariance
    stateCovar = masterStateWrapper->getStateErrorVariance();

    diagStateCov.resize(stateCovar.rows());
    for (size_t i = 0; i < (size_t)stateCovar.rows(); i++) {
        diagStateCov(i)=stateCovar(i,i);
    }
    //std::cout<< "INIT COVARIANCE DIAGONAL P(n+1)+n: " << diagStateCov.transpose() << std::endl;
    PRNS(" INIT COVARIANCE DIAGONAL P(n+1)+n:  \n" << diagStateCov.transpose());

    modelCovar = masterStateWrapper->getModelErrorVariance();
    //std::cout<< "Model covariance: " << modelCovar << std::endl;
    PRNS(" INIT COVARIANCE DIAGONAL P(n+1)+n:  \n" << modelCovar);

    stateExp = masterStateWrapper->getState();

    /// Compute Sigma Points
    switch (this->m_sigmaTopology) {
    case STAR:
        computeStarSigmaPoints(matI);
        break;
    case SIMPLEX:
    default:
        computeSimplexSigmaPoints(matI);
    }

    sigmaPointsNum = matI.rows();
    matXi.resize(stateSize, sigmaPointsNum);
    matXi.setZero();
    genMatXi.resize( sigmaPointsNum,stateSize);
    genMatXi.setZero();

    /// Initialise State Observation Mapping for Sigma Points
    m_sigmaPointObservationIndexes.resize(sigmaPointsNum);
}



template <class FilterType>
void UKFilterClassicOrig<FilterType>::stabilizeMatrix (EMatrixX& _initial, EMatrixX& _stabilized) {
    Eigen::JacobiSVD<Eigen::MatrixXd> svd(_initial, Eigen::ComputeThinU | Eigen::ComputeThinV);
    const Eigen::JacobiSVD<Eigen::MatrixXd>::SingularValuesType singVals = svd.singularValues();
    Eigen::JacobiSVD<Eigen::MatrixXd>::SingularValuesType singValsStab = singVals;
    for (int i=0; i < singVals.rows(); i++ ){
        if ((singValsStab(i)*singValsStab(i))*(1.0/(singVals(0)*singVals(0)))< 1.0e-6) singValsStab(i)=0;
    }
    _stabilized= svd.matrixU()*singValsStab*svd.matrixV().transpose();

}

template <class FilterType>
void UKFilterClassicOrig<FilterType>::pseudoInverse( EMatrixX& M,EMatrixX& pinvM) {
    double epsilon= 1e-15;
    Eigen::JacobiSVD<Eigen::MatrixXd> svd(M, Eigen::ComputeThinU | Eigen::ComputeThinV);
    const Eigen::JacobiSVD<Eigen::MatrixXd>::SingularValuesType singVals = svd.singularValues();
    Eigen::JacobiSVD<Eigen::MatrixXd>::SingularValuesType invSingVals = singVals;
    for(int i=0; i<singVals.rows(); i++) {
        if(singVals(i)*singVals(i) <= epsilon*epsilon) invSingVals(i) = 0.0;
        else invSingVals(i) = 1.0 / invSingVals(i);
    }
    Eigen::MatrixXd S_inv = invSingVals.asDiagonal();
    pinvM = svd.matrixV()*S_inv* svd.matrixU().transpose();
}

template <class FilterType>
void UKFilterClassicOrig<FilterType>::sqrtMat(EMatrixX& A, EMatrixX& sqrtA){
    double epsilon= 1e-15;
    Eigen::JacobiSVD<Eigen::MatrixXd> svd(A, Eigen::ComputeThinU | Eigen::ComputeThinV);
    const Eigen::JacobiSVD<Eigen::MatrixXd>::SingularValuesType singVals = svd.singularValues();
    Eigen::JacobiSVD<Eigen::MatrixXd>::SingularValuesType sqrtSingVals = singVals;
    for(int i=0; i<singVals.rows(); i++) {
        if(singVals(i)*singVals(i) <= epsilon*epsilon) sqrtSingVals(i) = 0.0;
        else sqrtSingVals(i) = sqrt(sqrtSingVals(i));
    }
    Eigen::MatrixXd S_inv = sqrtSingVals.asDiagonal();
    sqrtA = svd.matrixV()*S_inv* svd.matrixU().transpose();

}

template <class FilterType>
void UKFilterClassicOrig<FilterType>::writeValidationPlot (std::string filename ,EVectorX& state ){
    if (this->saveParam) {
        std::ofstream paramFile(filename.c_str(), std::ios::app);
        if (paramFile.is_open()) {
            paramFile << state.transpose() << "";
            paramFile << '\n';
            paramFile.close();
        }
    }
}

template <class FilterType>
void UKFilterClassicOrig<FilterType>::computeSimplexSigmaPoints(EMatrixX& sigmaMat) {
    size_t p = stateSize;
    size_t r = stateSize + 1;

    EMatrixX workingMatrix = EMatrixX::Zero(p, r);

    Type scal, beta, sqrt_p;
    beta = Type(p) / Type(p+1);
    sqrt_p = sqrt(Type(p));
    scal = Type(1.0)/sqrt(Type(2) * beta);
    workingMatrix(0,0) = scal;
    workingMatrix(0,1) = -scal;

    for (size_t i = 1; i < p; i++) {
        scal = Type(1.0) / sqrt(beta * Type(i+1) * Type(i+2));

        for (size_t j = 0; j < i+1; j++)
            workingMatrix(i,j) = -scal;
        workingMatrix(i,i+1) = Type(i+1) * scal;
    }


    sigmaMat.resize(r,p);
    for (size_t i = 0; i < r; i++)
        sigmaMat.row(i) = workingMatrix.col(i) * sqrt_p;

    vecAlpha.resize(r);
    vecAlpha.fill(Type(1.0)/Type(r));
    alphaConstant = true;
    alpha = vecAlpha(0);

    alphaVar = (this->useUnbiasedVariance.getValue()) ? Type(1.0)/Type(r-1) : Type(1.0)/Type(r);
    vecAlphaVar.resize(r);
    vecAlphaVar.fill(alphaVar);
    //PRNS("sigmaMat: \n" << sigmaMat);
    //PRNS("vecAlphaVar: \n" << vecAlphaVar);
    //std::cout<< "Sigma mat: " << sigmaMat << std::endl;
    //std::cout<< "vecAlphaVar: " << vecAlphaVar << std::endl;
}

template <class FilterType>
void UKFilterClassicOrig<FilterType>::computeStarSigmaPoints(EMatrixX& sigmaMat) {
    size_t p = stateSize;
    size_t r = 2 * stateSize + 1;

    EMatrixX workingMatrix = EMatrixX::Zero(p, r);

    Type lambda, sqrt_vec;
    lambda = this->lambdaScale.getValue();
    PRNS("lambda scale equals: " << lambda);
    sqrt_vec = sqrt(p + lambda);

    for (size_t j = 0; j < p; j++) {
        workingMatrix(j,j) = sqrt_vec;
    }
    for (size_t j = p; j < 2 * p; j++) {
        workingMatrix(2*p-j-1,j) = -sqrt_vec;
    }

    sigmaMat.resize(r,p);
    for (size_t i = 0; i < r; i++)
        sigmaMat.row(i) = workingMatrix.col(i);

    vecAlpha.resize(r);
    vecAlpha.fill(Type(1.0)/Type(2 * (p + lambda)));
    vecAlpha(2 * p) = Type(lambda) / Type(p + lambda);
    alphaConstant = false;
    alpha = vecAlpha(0);

    alphaVar = (this->useUnbiasedVariance.getValue()) ? Type(1.0)/Type(2 * (p + lambda) - 1) : Type(1.0)/Type(2 * (p + lambda));
    vecAlphaVar.resize(r);
    vecAlphaVar.fill(alphaVar);
    vecAlphaVar(2 * p) = Type(lambda) / Type(p + lambda);
    //PRNS("sigmaMat: \n" << sigmaMat);
    //PRNS("vecAlphaVar: \n" << vecAlphaVar);
    //std::cout<< "Sigma mat: " << sigmaMat << std::endl;
    //std::cout<< "vecAlphaVar: " << vecAlphaVar << std::endl;
}

template <class FilterType>
void UKFilterClassicOrig<FilterType>::draw(const core::visual::VisualParams* vparams ) {
    if(d_draw.getValue()){
        if (vparams->displayFlags().getShowVisualModels()) {
            std::vector<std::vector<sofa::defaulttype::Vec3d>> predpoints;
            predpoints.resize(sigmaPointsNum);
            for(  std::vector<std::vector<sofa::defaulttype::Vec3d>>::iterator it = predpoints.begin(); it != predpoints.end(); ++it)
            {
                it->resize( d_MOnodes_draw.getValue() );
            }

            for(unsigned i=0; i < sigmaPointsNum; i++){
                EVectorX coll = genMatXi.row(i);

                for (unsigned j=0; j < d_MOnodes_draw.getValue(); j++){
                    for (unsigned k=0; k < 3; k++){
                        if  (masterStateWrapper->estimOnlyXYZ())
                                predpoints[i][j][k]=coll(3*j+k);
                        else
                            predpoints[i][j][k]=coll(6*j+k);
                    }
                }


                Vec4f color;

                switch (i) {
                case 0: color = Vec4f(1.0,0.0,0.0,1.0); break;
                case 1: color = Vec4f(0.0,1.0,0.0,1.0); break;
                case 2: color = Vec4f(0.0,0.0,1.0,1.0); break;
                default: color = Vec4f(0.5, 0.5, 0.5, 0.5);
                }
                helper::vector<double>  colorB;
                colorB.resize(this->stateSize);
                for(size_t i =0; i < colorB.size(); i++){

                    colorB[i]= ((double) rand() / (RAND_MAX)) ;
                }

                vparams->drawTool()->drawSpheres(predpoints[i],  d_radius_draw.getValue(), sofa::defaulttype::Vec<4, float>(m_omega,0.0f,0.0f,1.0f));
            }
//                if (d_MOnodes_draw.getValue()>=2)
//                    vparams->drawTool()->drawLineStrip(predpoints[i],3.0,sofa::defaulttype::Vec<4, float>(color[i],0.5f,colorB[i],1.0f));
//          }

        }
    }
}



} // stochastic
} // component
} // sofa

#endif // UKFilterClassicOrig_INL


/*matPxzB.fill(FilterType(0.0));
matPzB.fill(FilterType(0.0));

EVectorX vx(stateSize), z(observationSize), vz(observationSize);
vx.fill(FilterType(0.0));
vz.fill(FilterType(0.0));
z.fill(FilterType(0.0));
for (size_t i = 0; i < sigmaPointsNum; i++) {
   vx = matXi.col(i) - stateExp;
   z = matZmodel.col(i);
   vz = z - predObsExp;
   for (size_t x = 0; x < stateSize; x++)
       for (size_t y = 0; y < observationSize; y++)
           matPxzB(x,y) += vx(x)*vz(y);

   for (size_t x = 0; x < observationSize; x++)
       for (size_t y = 0; y < observationSize; y++)
           matPzB(x,y) += vz(x)*vz(y);
}
matPxzB = alphaVar * matPxzB;
matPzB = alphaVar * matPzB + obsCovar;*/

/*
    stateCovar.fill(FilterType(0.0));
    EVectorX tmpX(stateSize);
    tmpX.fill(FilterType(0.0));
    for (size_t i = 0; i < sigmaPointsNum; i++) {
       tmpX = matXi.col(i) - stateExp;
       for (size_t x = 0; x < stateSize; x++)
           for (size_t y = 0; y < stateSize; y++)
               stateCovar(x,y) += tmpX(x)*tmpX(y);
    }
    stateCovar=alphaVar*stateCovar;
}*/
