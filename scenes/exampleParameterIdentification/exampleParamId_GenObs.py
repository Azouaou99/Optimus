import Sofa
import math
import os
import sys
import csv
import yaml
import pprint
import numpy as np
import time

__file = __file__.replace('\\', '/') # windows

def createScene(rootNode):
    rootNode.createObject('RequiredPlugin', name='Optimus', pluginName='Optimus')
    rootNode.createObject('RequiredPlugin', name='Pardiso', pluginName='SofaPardisoSolver')
    rootNode.createObject('RequiredPlugin', name='IMAUX', pluginName='ImageMeshAux')
    
	# load YAML configuration given as argument via --argv name.yaml    
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
    
    AppStiff_GenObs(rootNode, options)

    return 0;

class AppStiff_GenObs(Sofa.PythonScriptController):

    def __init__(self, rootNode, opt):       
        self.opt = opt

        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(opt)
        
        self.folder = opt['io']['folder']                        
        
        # create folder to save the observations; back-up if the folder exists already
        stamp='_'+str(int(time.time()))
        os.system('mkdir -p arch')
        os.system('mv --backup -S '+stamp+' '+self.folder+' arch')
        os.system('mkdir -p '+self.folder)
    
        # create folder to save the VTK geometry 
        if opt['io']['saveGeo']:
            self.geoFolder = self.folder+'/obsGeometry'
            os.system('mkdir -p '+self.geoFolder)

        self.createGraph(rootNode)

        return None;

    def createGraph(self,rootNode):
        self.step = 0          
        self.incStep = 0     
        rootNode.findData('dt').value = self.opt['model']['dt']
        rootNode.findData('gravity').value = self.opt['model']['gravity']

        rootNode.createObject('VisualStyle', displayFlags='showBehaviorModels showForceFields showCollisionModels hideVisual')
                        
        # rootNode/simuNode
        simuNode = rootNode.createChild('simuNode')        
        simuNode.createObject('MeshVTKLoader', name='loader', filename=self.opt['model']['volumeMesh'])

        # integration in time
        intType = self.opt['model']['int']['type']
        if intType == 'Euler':            
            simuNode.createObject('EulerImplicitSolver', firstOrder = self.opt['model']['int']['first_order'], rayleighStiffness=self.opt['model']['int']['rstiff'], rayleighMass=self.opt['model']['int']['rmass'])
        elif intType == 'Newton':            
            simuNode.createObject('NewtonStaticSolver', maxIt=self.opt['model']['int']['maxit'], correctionTolerance='1e-8', residualTolerance='1e-8', convergeOnResidual='1', printLog=self.opt['model']['int']['verbose'])       
        
        simuNode.createObject('SparsePARDISOSolver', name='lsolver', verbose='0', symmetric=self.opt['model']['linsol']['pardisoSym'], exportDataToFolder=self.opt['model']['linsol']['pardisoFolder'])
        simuNode.createObject('MechanicalObject', src='@loader', name='Volume')        
        simuNode.createObject('BoxROI', box=self.opt['model']['bc']['boxes'], name='fixedBox', drawBoxes='1')
        simuNode.createObject('FixedConstraint', indices='@fixedBox.indices')        
        simuNode.createObject('TetrahedronSetTopologyContainer', name="Container", src="@loader", tags=" ")
        simuNode.createObject('TetrahedronSetTopologyModifier', name="Modifier")        
        simuNode.createObject('TetrahedronSetTopologyAlgorithms', name="TopoAlgo")
        simuNode.createObject('TetrahedronSetGeometryAlgorithms', name="GeomAlgo")
        #simuNode.createObject('ShowSpheres', position='@Volume.position', color='0 1 0 1', radius='0.001')
        
        simuNode.createObject('MeshMatrixMass', printMass='0', lumping='1', massDensity=self.opt['model']['density'], name='mass')

        # physics forcefield        
        method = self.opt['model']['fem']['method']
        E=self.opt['model']['fem']['young_modulus']
        nu=self.opt['model']['fem']['poisson_ratio']        
        if  method[0:3] == 'Cor':
            simuNode.createObject('TetrahedronFEMForceField', name='FEM', method=method[3:].lower(), listening='true', drawHeterogeneousTetra='1', 
                poissonRatio=nu, youngModulus=E, updateStiffness='1')
        elif method == 'StVenant':
            simuNode.createObject('Indices2ValuesTransformer', name='pm', indices=[1], values1=E, values2=nu, inputValues='@loader.dataset', transformation='ENu2MuLambda')
            simuNode.createObject('TetrahedralTotalLagrangianForceField', name='FEM', materialName='StVenantKirchhoff', ParameterSet='@pm.outputValues')

        # excitations
        simuNode.createObject('BoxROI', name='forceBox', box=self.opt['model']['applied_force']['boxes'], drawBoxes='1')
        self.appliedForce = simuNode.createObject('ConstantForceField', force=self.opt['model']['applied_force']['initial_force'], indices='@forceBox.indices')
        
        # export geometry in VTK files in each step
        if self.opt['io']['saveGeo']:
            simuNode.createObject('VTKExporter', filename=self.geoFolder+'/object.vtk', XMLformat='0',listening='1',edges="0",triangles="0",quads="0",tetras="1",
                exportAtBegin="1", exportAtEnd="0", exportEveryNumberOfSteps="1", printLog='0')

        
        obsNode = simuNode.createChild('obsNode')
        obsNode.createObject('MeshVTKLoader', name='obsloader', filename=self.opt['model']['observationPoints'])
        obsNode.createObject('MechanicalObject', src='@obsloader', name='MO')
        obsNode.createObject('BarycentricMapping')
        obsNode.createObject('BoxROI', name='observationBox', box='-1 -1 -1 1 1 1')        
        obsNode.createObject('ShowSpheres', radius="0.002", color="1 0 0 1", position='@MO.position')
        if self.opt['io']['saveObs']:
            obsFile = self.folder + '/' + self.opt['io']['obsFile']
            obsNode.createObject('OptimMonitor', name='ObservationMonitor', indices='@observationBox.indices', ExportPositions='1', fileName=obsFile, ExportVelocities='0', ExportForces='0')
             

        # rootNode/simuNode/oglNode
        oglNode = simuNode.createChild('oglNode')
        self.oglNode = oglNode
        oglNode.createObject('MeshSTLLoader', name='objectSLoader', filename=self.opt['model']['surfaceMesh'])
        oglNode.createObject('OglModel', color='0 0 1 1')
        oglNode.createObject('BarycentricMapping')        
        

        return 0;

    def onBeginAnimationStep(self, deltaTime):
        self.step += 1
        if 'applied_force' in self.opt['model'].keys():
            maxTS = self.opt['model']['applied_force']['num_inc_steps']
            delta = np.array(self.opt['model']['applied_force']['delta'])
            if self.step < maxTS:
                fc = np.array(self.appliedForce.findData('force').value)
                fc[0] += delta
                self.appliedForce.findData('force').value = fc.tolist()       
        
        return 0


    def onEndAnimationStep(self, deltaTime):
        
        return 0;
