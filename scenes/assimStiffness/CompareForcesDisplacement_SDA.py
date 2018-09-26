import Sofa
import math
import os
import sys
import csv
import yaml
import pprint
import numpy as np

__file = __file__.replace('\\', '/') # windows

def createScene(rootNode):
    rootNode.createObject('RequiredPlugin', name='Optimus', pluginName='Optimus')
    rootNode.createObject('RequiredPlugin', name='Pardiso', pluginName='SofaPardisoSolver')
    rootNode.createObject('RequiredPlugin', name='IMAUX', pluginName='ImageMeshAux')
    # rootNode.createObject('RequiredPlugin', name='MJED', pluginName='SofaMJEDFEM')
    
    try : 
        sys.argv[0]
    except :
        commandLineArguments = []
    else :
        commandLineArguments = sys.argv
    

    if len(commandLineArguments) > 1:
        configFileName = commandLineArguments[1]
    else:
        print 'ERROR: Must supply a yaml config file as an argument!'
        return


    with open(configFileName, 'r') as stream:
        try:
            options = yaml.load(stream)            

        except yaml.YAMLError as exc:
            print(exc)
            return
    
    AppliedForces_SDA(rootNode, options)

    return 0;


class AppliedForces_SDA(Sofa.PythonScriptController):

    def __init__(self, rootNode, opt):
        self.opt = opt

        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(opt)
                                        
        self.saveEst = opt['io']['saveEst']
        self.saveGeo = opt["io"]["saveGeo"]
                            
        prefix = opt['io']['prefix']
        suffix = opt['io']['suffix']
        
        self.mainFolder = prefix + opt['model']['int']['type'] + str(opt['model']['int']['maxit']) + suffix    
        self.obsFile = self.mainFolder + '/' + opt['io']['obsFileName']

        self.estFolder = self.mainFolder + '/' + opt['filter']['kind'] + '_' + opt['filter']['obs_tag'] + '_' + str(opt['model']['linsol']['usePCG']) + opt['io']['sdaFolderSuffix']

        if self.saveEst:                        
            os.system('mv '+self.estFolder+' '+self.estFolder+'_arch')
            os.system('mkdir '+self.estFolder)

            self.stateExpFile=self.estFolder+'/state.txt'
            self.stateVarFile=self.estFolder+'/variance.txt'
            self.stateCovarFile=self.estFolder+'/covariance.txt'
            os.system('rm '+self.stateExpFile)
            os.system('rm '+self.stateVarFile)
            os.system('rm '+self.stateCovarFile)

            # create file with parameters and additional information
            self.opt['visual_parameters'] = {}
            self.opt['visual_parameters']['state_file_name'] = self.stateExpFile[self.stateExpFile.rfind('/') + 1:]
            self.opt['visual_parameters']['variance_file_name'] = self.stateVarFile[self.stateVarFile.rfind('/') + 1:]
            self.opt['visual_parameters']['covariance_file_name'] = self.stateCovarFile[self.stateCovarFile.rfind('/') + 1:]
            self.informationFileName = self.estFolder + '/daconfig.yml'
            with open(self.informationFileName, 'w') as stream:
                try:
                    yaml.dump(self.opt, stream, default_flow_style=False)
                except yaml.YAMLError as exc:
                    print(exc)

        if self.saveGeo:
            self.geoFolder = self.estFolder + '/VTK'
            os.system('mkdir -p '+self.geoFolder)

        self.numStep = 0
        self.actualPressure = [0, 0, 0]

        self.createGraph(rootNode)
        if opt['time']['time_profiling']:
            self.createTimeProfiler()

        return

    def createGraph(self,rootNode):
        self.rootNode=rootNode
        self.iterations = 0
        
        rootNode.findData('dt').value = self.opt['model']['dt']
        rootNode.findData('gravity').value = self.opt['model']['gravity']
        
        #rootNode.createObject('ViewerSetting', cameraMode='Perspective', resolution='1000 700', objectPickingMethod='Ray casting')
        rootNode.createObject('VisualStyle', name='VisualStyle', displayFlags='showBehaviorModels showForceFields showCollisionModels hideVisualModels')

        rootNode.createObject('FilteringAnimationLoop', name="StochAnimLoop", verbose="1")

        self.filterKind = self.opt['filter']['kind']
        if self.filterKind == 'ROUKF':
            self.filter = rootNode.createObject('ROUKFilter', name="ROUKF", verbose="1", useBlasToMultiply='1', sigmaTopology=self.opt['filter']['sigma_points_topology'])
            estimatePosition = 1            
        elif self.filterKind == 'UKFSimCorr':
            self.filter = rootNode.createObject('UKFilterSimCorr', name="UKFSC", verbose="1", sigmaTopology=self.opt['filter']['sigma_points_topology'])
            estimatePosition = 0
        elif self.filterKind == 'UKFClassic':
            self.filter = rootNode.createObject('UKFilterSimCorr', name="UKFClas", verbose="1", sigmaTopology=self.opt['filter']['sigma_points_topology'], exportPrefix=self.estFolder)
            estimatePosition = 1
            
        rootNode.createObject('MeshVTKLoader', name='loader', filename=self.opt['model']['vol_mesh'])
        rootNode.createObject('MeshSTLLoader', name='sloader', filename=self.opt['model']['surf_mesh'])
    
        # /ModelNode
        modelNode=rootNode.createChild('ModelNode')
        modelNode.createObject('StochasticStateWrapper',name="StateWrapper",verbose='1', estimatePosition=estimatePosition, estimateVelocity='0')
        
        # /ModelNode/cylinder
        simuNode=modelNode.createChild('cylinder')  

        intType = self.opt['model']['int']['type']
        intMaxit = self.opt['model']['int']['maxit']
        rmass = self.opt['model']['int']['rmass']
        rstiff = self.opt['model']['int']['rstiff']

        if intType == 'Euler':
            simuNode.createObject('EulerImplicitSolver', rayleighStiffness=rstiff, rayleighMass=rmass)
        elif intType == 'Newton':
            simuNode.createObject('NewtonStaticSolver', name="NewtonStatic", printLog="0", correctionTolerance="1e-8", residualTolerance="1e-8", convergeOnResidual="1", maxIt="2")           

        
        if self.opt['model']['linsol']['usePCG']:
            simuNode.createObject('StepPCGLinearSolver', name='lsolverit', precondOnTimeStep='1', use_precond='1', tolerance='1e-10', iterations='500',
                verbose='1', listening='1', update_step=self.opt['model']['linsol']['PCGUpdateSteps'], preconditioners='lsolver')

        simuNode.createObject('SparsePARDISOSolver', name='lsolver', verbose='0', symmetric=self.opt['model']['linsol']['pardisoSym'], exportDataToFolder=self.opt['model']['linsol']['pardisoFolder'])
        
        simuNode.createObject('MechanicalObject', src="@/loader", name="Volume")        
        simuNode.createObject('TetrahedronSetTopologyContainer', name="Container", src="@/loader", tags=" ")
        simuNode.createObject('TetrahedronSetTopologyModifier', name="Modifier")        
        simuNode.createObject('TetrahedronSetTopologyAlgorithms', name="TopoAlgo")
        simuNode.createObject('TetrahedronSetGeometryAlgorithms', name="GeomAlgo")

        if 'total_mass' in self.opt['model'].keys():
            simuNode.createObject('UniformMass', totalMass=self.opt['model']['total_mass'])

        if 'density' in self.opt['model'].keys():
            simuNode.createObject('MeshMatrixMass', printMass='0', lumping='1', massDensity=self.opt['model']['density'], name='mass')    
        
        simuNode.createObject('OptimParams', name="paramE", optimize="1", template="Vector", 
            numParams=self.opt['filter']['nparams'], transformParams=self.opt['filter']['param_transform'],
            initValue=self.opt['filter']['param_init_exval'], stdev=self.opt['filter']['param_init_stdev'],
            minValue=self.opt['filter']['param_min_val'], maxValue=self.opt['filter']['param_max_val'])

        youngModuli=self.opt['model']['young_moduli']
        indices = range(1, len(youngModuli)+1)
        simuNode.createObject('Indices2ValuesMapper', indices=indices, values='@paramE.value', name='youngMapper', inputValues='@/loader.dataset')

        simuNode.createObject('TetrahedronFEMForceField', name='FEM', updateStiffness='1', listening='true', drawHeterogeneousTetra='1', method='large', poissonRatio='0.45', youngModulus='@youngMapper.outputValues')

        controlType = self.opt['model']['control']['type']        
        if controlType == 'pressure':
            surfNode=simuNode.createChild('surfaceNode')
            surfNode.createObject('MeshSTLLoader', name='loader', filename=self.opt['model']['surf_mesh'])
            surfNode.createObject('MechanicalObject', src='@loader', name='surface')
            surfNode.createObject('TriangleSetTopologyContainer', name="Container", src="@loader", tags=" ")
            surfNode.createObject('TriangleSetTopologyModifier', name="Modifier")        
            surfNode.createObject('TriangleSetTopologyAlgorithms', name="TopoAlgo")
            surfNode.createObject('TriangleSetGeometryAlgorithms', name="GeomAlgo")
            self.pressureField = surfNode.createObject('TrianglePressureForceField', name='forceField', normal='0 0 1', showForces='1', dmin=0.299, dmax=0.301)
            surfNode.createObject('BarycentricMapping', name='mapping')



        simuNode.createObject('BoxROI', box=self.opt['model']['bc']['boxes'], name='fixedBox')
        simuNode.createObject('FixedConstraint', indices='@fixedBox.indices')        

        if self.saveGeo:
            simuNode.createObject('VTKExporterDA', filename=self.geoFolder+'/object.vtk', XMLformat='0',listening='1',edges="0",triangles="0",quads="0",tetras="1",
                exportAtBegin="1", exportAtEnd="0", exportEveryNumberOfSteps="1")
            

        # /ModelNode/cylinder/observations
        obsNode = simuNode.createChild('observations')
        obsNode.createObject('MeshVTKLoader', name='obsloader', filename=self.opt['filter']['obs_points'])
        obsNode.createObject('MechanicalObject', name='SourceMO', position='@obsloader.position')
        # obsNode.createObject('MechanicalObject', name='SourceMO', position='0.02 0 0.08 0.02 0 0.16    0.0141 0.0141 0.08    0.0141 -0.0141 0.08    0.0141 0.0141 0.16    0.0141 -0.0141 0.16    0.02 0 0.0533    0.02 0 0.107   \
        #     0.02 0 0.133    0.02 0 0.187    0.02 0 0.213    0.0175 0.00961 0.0649    0.00925 0.0177 0.0647    0.0139 0.0144 0.0398    0.00961 -0.0175 0.0649    0.0177 -0.00925 0.0647  \
        #     0.0144 -0.0139 0.0402    0.0177 0.00936 0.145    0.0095 0.0176 0.145    0.0175 0.00961 0.0951    0.00925 0.0177 0.0953    0.0139 0.0144 0.12    0.00937 -0.0177 0.145   \
        #     0.0176 -0.00949 0.145    0.00935 -0.0177 0.0953    0.0176 -0.00949 0.095    0.0142 -0.0141 0.12    0.0177 0.00937 0.175    0.00949 0.0176 0.175    0.014 0.0143 0.2   \
        #     0.00959 -0.0175 0.175    0.0177 -0.00924 0.175    0.0143 -0.014 0.2')

        obsNode.createObject('VTKExporter', name='temporaryExporter', filename='tempObs.vtk', XMLformat='0',listening='1',edges="0",triangles="0",quads="0",tetras="0",
                exportAtBegin="1", exportAtEnd="0", exportEveryNumberOfSteps="0", position='@SourceMO.position')
        
        obsNode.createObject('BarycentricMapping')
        obsNode.createObject('MappedStateObservationManager', name="MOBS", listening="1", stateWrapper="@../../StateWrapper", verbose="1",
                    observationStdev=self.opt['filter']['observ_stdev'], noiseStdev=self.opt['filter']['obs_added_noise_var'])
        obsNode.createObject('SimulatedStateObservationSource', name="ObsSource", monitorPrefix=self.obsFile)
        obsNode.createObject('ShowSpheres', radius="0.002", color="1 0 0 1", position='@SourceMO.position')
        obsNode.createObject('ShowSpheres', radius="0.0015", color="1 1 0 1", position='@MOBS.mappedObservations')


        # /ModelNode/cylinder/visualization
        oglNode = simuNode.createChild('visualization')
        self.oglNode = oglNode
        oglNode.createObject('OglModel', color='1 0 0 1')
        oglNode.createObject('BarycentricMapping')        
        
                
        return 0

    def createTimeProfiler(self):
        print 'Time statistics file: ' + self.estFolder + '/' + self.opt['time']['time_statistics_file']
        Sofa.timerSetInterval(self.opt['time']['timer_name'], self.opt['time']['iterations_interval'])    # Set the number of steps neded to compute the timer
        Sofa.timerSetOutputType(self.opt['time']['timer_name'], 'json')    # Set output file format
        with open(self.estFolder + '/' + self.opt['time']['time_statistics_file'], "a") as outputFile:
            outputFile.write('{')
            outputFile.close()

        return 0


    def initGraph(self,node):
        print 'Init graph called (python side)'
        self.step    =     0
        self.total_time =     0            
        return 0

    def bwdInitGraph(self, node):
    	self.exportStochasticState()
    	return 0

    def onBeginAnimationStep(self, deltaTime):
        if self.opt['time']['time_profiling']:
            Sofa.timerSetEnabled(self.opt['time']['timer_name'], True)
            Sofa.timerBegin(self.opt['time']['timer_name'])

        self.numStep += 1

        if self.numStep <= self.opt['model']['control']['nsteps']:
            self.actualPressure = map(sum, zip(self.actualPressure, self.opt['model']['control']['deltaPressure']))
        self.pressureField.pressure = self.actualPressure

        print 'Setting actual pressure: ',self.actualPressure


        return 0

    def onEndAnimationStep(self, deltaTime):
        self.iterations = self.iterations + 1
        self.exportStochasticState()
        self.saveTimeStatistics()



        # print self.basePoints.findData('indices_position').value

        return 0

    def saveTimeStatistics(self):
        if self.opt['time']['time_profiling']:
            if self.iterations <= self.opt['time']['iteration_amount']:
                result = Sofa.timerEnd(self.opt['time']['timer_name'], self.rootNode)
                if result != None :
                    with open(self.estFolder + '/' + self.opt['time']['time_statistics_file'], "a") as outputFile:
                        outputFile.write(result + ",")
                        outputFile.close()
            # replace last symbol
            if self.iterations == self.opt['time']['iteration_amount']:
                with open(self.estFolder + '/' + self.opt['time']['time_statistics_file'], "a") as outputFile:
                    outputFile.seek(-1, os.SEEK_END)
                    outputFile.truncate()
                    outputFile.write("\n}")
                    outputFile.close()

        return 0


    def exportStochasticState(self):
    	if self.saveEst:              
            stateName = 'reducedState' if self.filterKind == 'ROUKF' else 'state'
            varName = 'reducedVariance' if self.filterKind == 'ROUKF' else 'variance'
            covarName = 'reducedCovariance' if self.filterKind == 'ROUKF' else 'covariance'
        
            rs=self.filter.findData(stateName).value
            state = [val for sublist in rs for val in sublist]
            print 'State:',state            
            #print reducedState

            f1 = open(self.stateExpFile, "a")        
            f1.write(" ".join(map(lambda x: str(x), state)))
            f1.write('\n')
            f1.close()    
                    
            rv=self.filter.findData(varName).value
            variance = [val for sublist in rv for val in sublist]
            print 'Stdev: ', np.sqrt(variance)
            #print 'Reduced variance:'
            #print reducedVariance

            f2 = open(self.stateVarFile, "a")        
            f2.write(" ".join(map(lambda x: str(x), variance)))
            f2.write('\n')
            f2.close()

            rcv=self.filter.findData(covarName).value
            covariance = [val for sublist in rcv for val in sublist]
            print 'Covariance: ', covariance
            #print 'Reduced Covariance:'
            #print reducedCovariance

            f3 = open(self.stateCovarFile, "a")
            f3.write(" ".join(map(lambda x: str(x), covariance)))
            f3.write('\n')
            f3.close()    

            return

    def cleanup(self):
        if self.saveEst:
            print 'Estimations saved to '+self.estFolder

        if self.saveGeo:
            print 'Geometries saved to '+self.geoFolder

        return 0;

    def onScriptEvent(self, senderNode, eventName,data):        
        return 0;
