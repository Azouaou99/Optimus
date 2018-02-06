import Sofa
import math
import os
import sys
import csv
sys.path.append(os.getcwd() + '/../assimStiffness')
import DAOptions

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
    mycylGravity_GenObs = cylGravity_GenObs(rootNode, commandLineArguments)
    return 0;


class cylGravity_GenObs (Sofa.PythonScriptController):

    options = DAOptions.DAOptions()

    def __init__(self, rootNode, commandLineArguments) :         

        # load configuration from yaml file
        if len(commandLineArguments) > 1:
            self.configFileName = commandLineArguments[1]
        else:
            self.configFileName = "cyl_scene_config.yml"

        self.options.parseYaml(self.configFileName)

        rootNode.findData('dt').value = self.options.model.dt
        rootNode.findData('gravity').value = self.options.model.gravity

        print "Command line arguments for python : "+str(commandLineArguments)
        self.createGraph(rootNode)

        return None;

    def createGraph(self,rootNode):
        
        # rootNode
        rootNode.createObject('RequiredPlugin', pluginName='Optimus')
        rootNode.createObject('RequiredPlugin', pluginName='SofaPardisoSolver')
        # rootNode.createObject('RequiredPlugin', pluginName='SofaMJEDFEM')
        rootNode.createObject('RequiredPlugin', pluginName='ImageMeshAux')
        rootNode.createObject('VisualStyle', displayFlags='showBehaviorModels showForceFields showCollisionModels hideVisual')

        # rootNode/simuNode
        simuNode = rootNode.createChild('simuNode')
        self.simuNode = simuNode
        simuNode.createObject('EulerImplicitSolver', rayleighStiffness=self.options.model.rayleighStiffness, rayleighMass=self.options.model.rayleighMass)
        simuNode.createObject('SparsePARDISOSolver', name='LDLsolver', verbose='0', symmetric='2', exportDataToFolder='')
        # simuNode.createObject('MeshVTKLoader', name='loader', filename=self.options.model.volumeFileName)
        simuNode.createObject('MeshGmshLoader', name='loader', filename=self.options.model.volumeFileName)
        simuNode.createObject('MechanicalObject', src='@loader', name='Volume')

        for index in range(0, len(self.options.model.bcList)):
            bcElement = self.options.model.bcList[index]
            simuNode.createObject('BoxROI', box=bcElement.boundBoxes, name='boundBoxes'+str(index), drawBoxes='0')
            if (bcElement.bcType == 'fixed'):
                simuNode.createObject('FixedConstraint', indices='@boundBoxes'+str(index)+'.indices')
            elif (bcElement.bcType == 'elastic'):
                simuNode.createObject('RestShapeSpringsForceField', stiffness=bcElement.boundaryStiffness, angularStiffness="1", points='@boundBoxes'+str(index)+'.indices')
            else:
                print 'Unknown type of boundary conditions'
        simuNode.createObject('TetrahedronSetTopologyContainer', name="Container", src="@loader", tags=" ")
        simuNode.createObject('TetrahedronSetTopologyModifier', name="Modifier")        
        simuNode.createObject('TetrahedronSetTopologyAlgorithms', name="TopoAlgo")
        simuNode.createObject('TetrahedronSetGeometryAlgorithms', name="GeomAlgo")
        simuNode.createObject('UniformMass', totalMass=self.options.model.totalMass)

        simuNode.createObject('TetrahedronFEMForceField', updateStiffness='1', name='FEM', listening='true', drawHeterogeneousTetra='1', method='large', youngModulus='5000', poissonRatio='0.45')

        if self.options.observations.save:
            simuNode.createObject('BoxROI', name='observationBox', box='-1 -1 -1 1 1 1')
            simuNode.createObject('Monitor', name='ObservationMonitor', indices='@observationBox.indices', fileName=self.options.observations.valueFileName, ExportPositions='1', ExportVelocities='0', ExportForces='0')

        # add constant force field
        simuNode.createObject('BoxROI', name='impactBounds', box='0.14 0.15 0.4 0.16 0.17 0.43')
        simuNode.createObject('ConstantForceField', name='appliedForce', indices='@impactBounds.indices', totalForce='0.0 -2.0 0.9')

        obsNode = simuNode.createChild('obsNode')        
        obsNode.createObject('MeshVTKLoader', name='obsLoader', filename=self.options.observations.positionFileName)        
        obsNode.createObject('MechanicalObject', name='SourceMO', src="@obsLoader")
        obsNode.createObject('BarycentricMapping')
        obsNode.createObject('BoxROI', name='observationNodeBox', box='-1 -1 -1 1 1 1')
        obsNode.createObject('Monitor', name='ObservationMonitor', indices='@observationNodeBox.indices', fileName='observations/node', ExportPositions='1', ExportVelocities='0', ExportForces='0')

        return 0;

    def onMouseButtonLeft(self, mouseX,mouseY,isPressed):
        ## usage e.g.
        #if isPressed : 
        #    print "Control+Left mouse button pressed at position "+str(mouseX)+", "+str(mouseY)
        return 0;

    def onKeyReleased(self, c):
        ## usage e.g.
        #if c=="A" :
        #    print "You released a"
        return 0;

    def initGraph(self, node):
        ## Please feel free to add an example for a simple usage in /home/ip/Work/sofa/MyPlugins/Optimus/scenes/assimStiffness//home/ip/Work/sofa/master/src/applications/plugins/SofaPython/scn2python.py
        return 0;

    def onKeyPressed(self, c):
        ## usage e.g.
        #if c=="A" :
        #    print "You pressed control+a"
        return 0;

    def onMouseWheel(self, mouseX,mouseY,wheelDelta):
        ## usage e.g.
        #if isPressed : 
        #    print "Control button pressed+mouse wheel turned at position "+str(mouseX)+", "+str(mouseY)+", wheel delta"+str(wheelDelta)
        return 0;

    def storeResetState(self):
        ## Please feel free to add an example for a simple usage in /home/ip/Work/sofa/MyPlugins/Optimus/scenes/assimStiffness//home/ip/Work/sofa/master/src/applications/plugins/SofaPython/scn2python.py
        return 0;

    def cleanup(self):
        ## Please feel free to add an example for a simple usage in /home/ip/Work/sofa/MyPlugins/Optimus/scenes/assimStiffness//home/ip/Work/sofa/master/src/applications/plugins/SofaPython/scn2python.py
        return 0;

    def onGUIEvent(self, strControlID,valueName,strValue):
        ## Please feel free to add an example for a simple usage in /home/ip/Work/sofa/MyPlugins/Optimus/scenes/assimStiffness//home/ip/Work/sofa/master/src/applications/plugins/SofaPython/scn2python.py
        return 0;

    def onEndAnimationStep(self, deltaTime):
        ## Please feel free to add an example for a simple usage in /home/ip/Work/sofa/MyPlugins/Optimus/scenes/assimStiffness//home/ip/Work/sofa/master/src/applications/plugins/SofaPython/scn2python.py
        return 0;

    def onLoaded(self, node):
        ## Please feel free to add an example for a simple usage in /home/ip/Work/sofa/MyPlugins/Optimus/scenes/assimStiffness//home/ip/Work/sofa/master/src/applications/plugins/SofaPython/scn2python.py
        return 0;

    def reset(self):
        ## Please feel free to add an example for a simple usage in /home/ip/Work/sofa/MyPlugins/Optimus/scenes/assimStiffness//home/ip/Work/sofa/master/src/applications/plugins/SofaPython/scn2python.py
        return 0;

    def onMouseButtonMiddle(self, mouseX,mouseY,isPressed):
        ## usage e.g.
        #if isPressed : 
        #    print "Control+Middle mouse button pressed at position "+str(mouseX)+", "+str(mouseY)
        return 0;

    def bwdInitGraph(self, node):
        ## Please feel free to add an example for a simple usage in /home/ip/Work/sofa/MyPlugins/Optimus/scenes/assimStiffness//home/ip/Work/sofa/master/src/applications/plugins/SofaPython/scn2python.py
        return 0;

    def onScriptEvent(self, senderNode, eventName,data):
        ## Please feel free to add an example for a simple usage in /home/ip/Work/sofa/MyPlugins/Optimus/scenes/assimStiffness//home/ip/Work/sofa/master/src/applications/plugins/SofaPython/scn2python.py
        return 0;

    def onMouseButtonRight(self, mouseX,mouseY,isPressed):
        ## usage e.g.
        #if isPressed : 
        #    print "Control+Right mouse button pressed at position "+str(mouseX)+", "+str(mouseY)
        return 0;

    def onBeginAnimationStep(self, deltaTime):
        ## Please feel free to add an example for a simple usage in /home/ip/Work/sofa/MyPlugins/Optimus/scenes/assimStiffness//home/ip/Work/sofa/master/src/applications/plugins/SofaPython/scn2python.py
        return 0;

