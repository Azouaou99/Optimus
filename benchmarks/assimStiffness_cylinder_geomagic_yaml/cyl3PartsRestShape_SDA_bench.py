import Sofa
import math
import os
import sys
import csv
import yaml
sys.path.append(os.getcwd() + '/../../python_src/utils')
from FileSystemUtils import FolderHandler

__file = __file__.replace('\\', '/') # windows

def createScene(rootNode):
    rootNode.createObject('RequiredPlugin', pluginName='Optimus')
    rootNode.createObject('RequiredPlugin', pluginName='SofaPardisoSolver')
    rootNode.createObject('RequiredPlugin', pluginName='ImageMeshAux')
    #rootNode.createObject('RequiredPlugin', pluginName='SofaMJEDFEM')
    
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
    print "Command line arguments for python : " + str(commandLineArguments)

    with open(configFileName, 'r') as stream:
        try:
            options = yaml.load(stream)

        except yaml.YAMLError as exc:
            print(exc)
            return

    cyl3PartsRestShape_SDA(rootNode, options, configFileName)
    return 0



# Class definition
class cyl3PartsRestShape_SDA(Sofa.PythonScriptController):

    def __init__(self, rootNode, options, configFileName):
        self.options = options
        self.cameraReactivated = False
        self.rootNode = rootNode

        self.folderName = 'roukf_testing'
        folderCreator = FolderHandler()
        folderCreator.createFolder(self.folderName, archiveResults=0)

        # create file with parameters and additional information
        self.options['visual_parameters'] = {}
        self.stateFileName = 'state_' + self.options['scene_parameters']['filtering_parameters']['output_files_suffix'] + '.txt'
        self.options['visual_parameters']['state_file_name'] = self.stateFileName
        self.varianceFileName = 'variance_' + self.options['scene_parameters']['filtering_parameters']['output_files_suffix'] + '.txt'
        self.options['visual_parameters']['variance_file_name'] = self.varianceFileName
        self.covarianceFileName = 'covariance_' + self.options['scene_parameters']['filtering_parameters']['output_files_suffix'] + '.txt'
        self.options['visual_parameters']['covariance_file_name'] = self.covarianceFileName
        self.innovationFileName = 'innovation_' + self.options['scene_parameters']['filtering_parameters']['output_files_suffix'] + '.txt'
        self.options['visual_parameters']['innovation_file_name'] = self.innovationFileName
        
        self.informationFileName = self.folderName + '/daconfig.yml'

        with open(self.informationFileName, 'w') as stream:
            try:
                yaml.dump(self.options, stream, default_flow_style=False)

            except yaml.YAMLError as exc:
                print(exc)
                return

        self.createGraph(rootNode)



    def createGraph(self, rootNode):

        self.rootNode=rootNode

        print "Create graph called (Python side)\n"

        self.lambdaScale = 1.0
        if self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'ROUKF':
            self.estimPosition='1'
            self.estimVelocity='0'

        if self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'UKFSimCorr':
            self.estimPosition='0'
            self.estimVelocity='0'

        if self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'UKFClassic':
            self.estimPosition='1'
            self.estimVelocity='0'

        self.createScene(rootNode)
        
        return 0

    
    def createGlobalComponents(self, rootNode):
        # scene global stuff                
        rootNode.findData('gravity').value = self.options['scene_parameters']['general_parameters']['gravity']
        rootNode.findData('dt').value = self.options['scene_parameters']['general_parameters']['delta_time']

        rootNode.createObject('ViewerSetting', cameraMode='Perspective', resolution='1000 700', objectPickingMethod='Ray casting')
        rootNode.createObject('VisualStyle', name='VisualStyle', displayFlags='showBehaviorModels showForceFields showCollisionModels')

        #node.createObject('FilteringAnimationLoop', name="StochAnimLoop", verbose="1")
        rootNode.createObject('FilteringAnimationLoop', name="StochAnimLoop", verbose="1", computationTimeFile=self.folderName+'/'+self.options['scene_parameters']['time_parameters']['computation_time_file_name'])

        if (self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'ROUKF'):
            self.filter = rootNode.createObject('ROUKFilter', name="ROUKF", verbose="1", useUnbiasedVariance=self.options['scene_parameters']['filtering_parameters']['use_unbiased_variance'], sigmaTopology=self.options['scene_parameters']['filtering_parameters']['sigma_points_topology'], lambdaScale=self.lambdaScale)
        elif (self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'UKFSimCorr'):
            self.filter = rootNode.createObject('UKFilterSimCorr', name="UKF", verbose="1", useUnbiasedVariance=self.options['scene_parameters']['filtering_parameters']['use_unbiased_variance'], sigmaTopology=self.options['scene_parameters']['filtering_parameters']['sigma_points_topology'], lambdaScale=self.lambdaScale)
        elif (self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'UKFClassic'):
            self.filter = rootNode.createObject('UKFilterClassic', name="UKFClas", verbose="1", exportPrefix=self.folderName, useUnbiasedVariance=self.options['scene_parameters']['filtering_parameters']['use_unbiased_variance'], sigmaTopology=self.options['scene_parameters']['filtering_parameters']['sigma_points_topology'], lambdaScale=self.lambdaScale)
        else:
            print 'Unknown filter type!'
            
        rootNode.createObject('MeshVTKLoader', name='loader', filename=self.options['scene_parameters']['system_parameters']['volume_file_name'])
        
        impactSimu = rootNode.createChild('externalImpSimu')
        impactSimu.createObject('PreStochasticWrapper')
        impactSimu.createObject('EulerImplicitSolver')
        impactSimu.createObject('CGLinearSolver')
        self.targetPoint = impactSimu.createObject('MechanicalObject', name="state", template='Vec3d', useTopology='false', position=self.options['scene_parameters']['impact_parameters']['position'])
        impactSimu.createObject('SimulatedStateObservationSource', name="ImpactSim", template='Vec3d', printLog="1", monitorPrefix=self.options['scene_parameters']['impact_parameters']['observation_file_name'], drawSize="0.0015", controllerMode="1")
        impactSimu.createObject('ShowSpheres', radius='0.005', color='1 0 1 1', position='@state.position')
        
        return 0        



    #components common for both master and slave: the simulation itself (without observations and visualizations)
    def createCommonComponents(self, node):                                  
        # node.createObject('StaticSolver', applyIncrementFactor="0")
        node.createObject('EulerImplicitSolver', rayleighStiffness=self.options['scene_parameters']['general_parameters']['rayleigh_stiffness'], rayleighMass=self.options['scene_parameters']['general_parameters']['rayleigh_mass'])
        # node.createObject('VariationalSymplecticSolver', rayleighStiffness=self.options['scene_parameters']['general_parameters']['rayleigh_stiffness'], rayleighMass=self.options['scene_parameters']['general_parameters']['rayleigh_mass'], newtonError='1e-12', steps='1', verbose='0')
        node.createObject('SparsePARDISOSolver', name="precond", symmetric="1", exportDataToFolder="", iterativeSolverNumbering="0")
        # node.createObject('NewtonStaticSolver', name="NewtonStatic", printLog="0", correctionTolerance="1e-8", residualTolerance="1e-8", convergeOnResidual="1", maxIt="2")   
        # node.createObject('StepPCGLinearSolver', name="StepPCG", iterations="10000", tolerance="1e-12", preconditioners="precond", verbose="1", precondOnTimeStep="1")

        self.sourcePoint = node.createObject('MechanicalObject', src="@/loader", name="Volume")
        node.createObject('TetrahedronSetTopologyContainer', name="Container", src="@/loader", tags=" ")
        node.createObject('TetrahedronSetTopologyModifier', name="Modifier")        
        node.createObject('TetrahedronSetTopologyAlgorithms', name="TopoAlgo")
        node.createObject('TetrahedronSetGeometryAlgorithms', name="GeomAlgo")
        if 'total_mass' in self.options['scene_parameters']['general_parameters'].keys():
            node.createObject('UniformMass', totalMass=self.options['scene_parameters']['general_parameters']['total_mass'])
        if 'density' in self.options['scene_parameters']['general_parameters'].keys():
            node.createObject('MeshMatrixMass', printMass='0', lumping='1', massDensity=self.options['scene_parameters']['general_parameters']['density'], name='mass')

        if 'boundary_conditions_list' in self.options['scene_parameters']['general_parameters'].keys():
            for index in range(0, len(self.options['scene_parameters']['general_parameters']['boundary_conditions_list'])):
                bcElement = self.options['scene_parameters']['general_parameters']['boundary_conditions_list'][index]
                print bcElement
                node.createObject('BoxROI', box=bcElement['boxes_coordinates'], name='boundBoxes'+str(index), drawBoxes='0', doUpdate='0')
                if bcElement['condition_type'] == 'fixed':
                    node.createObject('FixedConstraint', indices='@boundBoxes'+str(index)+'.indices')
                elif bcElement['condition_type'] == 'elastic':
                    node.createObject('RestShapeSpringsForceField', stiffness=bcElement['spring_stiffness_values'], angularStiffness="1", points='@boundBoxes'+str(index)+'.indices')
                else:
                    print 'Unknown type of boundary conditions'
                    
        node.createObject('OptimParams', name="paramE", optimize="1", numParams=self.options['scene_parameters']['filtering_parameters']['optim_params_size'], template="Vector", initValue=self.options['scene_parameters']['filtering_parameters']['initial_stiffness'], minValue=self.options['scene_parameters']['filtering_parameters']['minimal_stiffness'], maxValue=self.options['scene_parameters']['filtering_parameters']['maximal_stiffness'], stdev=self.options['scene_parameters']['filtering_parameters']['initial_standart_deviation'], transformParams=self.options['scene_parameters']['filtering_parameters']['transform_parameters'])
        node.createObject('Indices2ValuesMapper', name='youngMapper', indices='1 3', values='@paramE.value', inputValues='@/loader.dataset', defaultValue='6000')
        node.createObject('TetrahedronFEMForceField', name='FEM', updateStiffness='1', listening='true', drawHeterogeneousTetra='1', method='large', poissonRatio='0.45', youngModulus='@youngMapper.outputValues')

        node.createObject('BoxROI', name='impactBounds', box='-0.01 -0.02 0.1 0.01 -0.01 0.11', doUpdate='0')
        self.toolSprings = node.createObject('RestShapeSpringsForceField', name="impactSpring", stiffness="10000", angularStiffness='1', external_rest_shape='@/externalImpSimu/state', drawSpring='1', points='@impactBounds.indices')

        return 0



    def createMasterScene(self, node):
        node.createObject('StochasticStateWrapper',name="StateWrapper",verbose="1", estimatePosition=self.estimPosition, positionStdev=self.options['scene_parameters']['filtering_parameters']['positions_standart_deviation'], estimateVelocity=self.estimVelocity)
        
        self.createCommonComponents(node)

        obsNode = node.createChild('obsNode')        
        obsNode.createObject('MeshVTKLoader', name='obsLoader', filename=self.options['scene_parameters']['system_parameters']['observation_points_file_name'])
        obsNode.createObject('MechanicalObject', name='SourceMO', src="@obsLoader")
        obsNode.createObject('BarycentricMapping')
        obsNode.createObject('MappedStateObservationManager', name="MOBS", observationStdev=self.options['scene_parameters']['filtering_parameters']['observation_noise_standart_deviation'], noiseStdev="0.0", listening="1", stateWrapper="@../StateWrapper", verbose="1")
        obsNode.createObject('SimulatedStateObservationSource', name="ObsSource", monitorPrefix=self.options['scene_parameters']['system_parameters']['observation_file_name'])
        obsNode.createObject('ShowSpheres', radius="0.002", color="1 0 0 1", position='@SourceMO.position')
        obsNode.createObject('ShowSpheres', radius="0.0015", color="1 1 0 1", position='@MOBS.mappedObservations')

        return 0
  
    

    def createScene(self,node):
        # r_slaves = [] # list of created auxiliary nodes
        self.createGlobalComponents(node)
                
        masterNode=node.createChild('MasterScene')
        self.createMasterScene(masterNode)        
 
        return 0


    def initGraph(self,node):
        print 'Init graph called (python side)'
        self.step    =     0
        self.total_time =     0
        
        # self.process.initializationObjects(node)
        return 0

    def onEndAnimationStep(self, deltaTime):

        if self.options['scene_parameters']['filtering_parameters']['save_state']:
            if (self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'ROUKF'):
                st=self.filter.findData('reducedState').value
            elif (self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'UKFSimCorr' or self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'UKFClassic'):
                st=self.filter.findData('state').value

            state = [val for sublist in st for val in sublist]
            #print 'Reduced state:'
            #print reducedState

            self.stateExpValFile = self.folderName + '/' + self.stateFileName
            print 'Storing to', self.stateExpValFile
            f1 = open(self.stateExpValFile, "a")
            f1.write(" ".join(map(lambda x: str(x), state)))
            f1.write('\n')
            f1.close()

            if (self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'ROUKF'):
                var=self.filter.findData('reducedVariance').value
            elif (self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'UKFSimCorr' or self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'UKFClassic'):
                var=self.filter.findData('variance').value
                                
            variance = [val for sublist in var for val in sublist]
            #print 'Reduced variance:'
            #print reducedVariance

            self.stateVarFile = self.folderName + '/' + self.varianceFileName
            f2 = open(self.stateVarFile, "a")
            f2.write(" ".join(map(lambda x: str(x), variance)))
            f2.write('\n')
            f2.close()

            if (self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'ROUKF'):
                covar=self.filter.findData('reducedCovariance').value
            elif (self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'UKFSimCorr' or self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'UKFClassic'):
                covar=self.filter.findData('covariance').value
            
            covariance = [val for sublist in covar for val in sublist]
            #print 'Reduced Covariance:'
            #print reducedCovariance

            self.stateCovarFile = self.folderName + '/' + self.covarianceFileName
            f3 = open(self.stateCovarFile, "a")
            f3.write(" ".join(map(lambda x: str(x), covariance)))
            f3.write('\n')
            f3.close()

        if self.options['scene_parameters']['filtering_parameters']['save_internal_data']:
            if (self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'ROUKF'):
                innov=self.filter.findData('reducedInnovation').value
            elif (self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'UKFSimCorr' or self.options['scene_parameters']['filtering_parameters']['filter_kind'] == 'UKFClassic'):
                innov=self.filter.findData('innovation').value

            innovation = [val for sublist in innov for val in sublist]
            #print 'Reduced state:'
            #print reducedState

            self.innovationFile = self.folderName + '/' + self.innovationFileName
            f4 = open(self.innovationFile, "a")
            f4.write(" ".join(map(lambda x: str(x), innovation)))
            f4.write('\n')
            f4.close()      

        # print self.basePoints.findData('indices_position').value

        return 0

    def onScriptEvent(self, senderNode, eventName,data):        
        return 0;
