# PyQT/OpenGL example
import ctypes
import os
from math import copysign

import numpy
from PyQt5 import QtGui, QtWidgets, QtCore

SHADERPATH = './'


def parseShader(file: str, program: QtGui.QOpenGLShaderProgram):
    def readStrings(inFile: file):
        source = ''
        lines = []
        lastpos = inFile.tell()
        for data in iter(inFile.readline, ''):
            if "#shader" in data:
                break
            elif data == eof:
                break
            lines.append(data)
            lastpos = inFile.tell()

        inFile.seek(lastpos)
        return source.join(lines)

    file = open(file, 'r')
    file.readlines()
    eof = file.tell()  # get location of EOF character.
    file.seek(0, 0)  # go back to file beginning.
    vs = ''
    fs = ''
    while True:
        line = file.readline()
        if file.tell() == eof:
            # Reached EOF.
            break
        elif not line:
            continue
        elif line == "#shader vertex\n":
            vs = readStrings(file)
        elif line == "#shader fragment\n":
            fs = readStrings(file)
    program.addShaderFromSourceCode(QtGui.QOpenGLShader.Vertex, vs)
    program.addShaderFromSourceCode(QtGui.QOpenGLShader.Fragment, fs)
    if not program.link():
        log = program.log()
        print(log)
        return False
    else:
        return True


class Window(QtWidgets.QMainWindow):
    def __init__(self, app):
        super().__init__()

        self.app = app
        self.app.mainwindow = self
        self.glviewPort = GLViewport(parent=self)
        self.glviewPort.setMinimumSize(600, 600)
        self.glviewPort.setMouseTracking(True)
        self.glviewPort.grabKeyboard()
        self.setCentralWidget(self.glviewPort)

    def closeEvent(self, event: QtGui.QCloseEvent):
        self.glviewPort.flush()
        return super().closeEvent(event)


class GraphicsObject:
    def __init__(self, name=None):
        self.name = name
        self.vao = QtGui.QOpenGLVertexArrayObject()
        self.vbo = QtGui.QOpenGLBuffer(QtGui.QOpenGLBuffer.VertexBuffer)
        self.ebo = QtGui.QOpenGLBuffer(QtGui.QOpenGLBuffer.IndexBuffer)
        self.vertices = []
        self.vertdtype = None
        self.indices = []
        self.idxdtype = None
        self.modelMatrix = QtGui.QMatrix4x4()
        self.modelMatrix.setToIdentity()
        self.viewMatrix = QtGui.QMatrix4x4()
        self.viewMatrix.setToIdentity()
        self.projMatrix = QtGui.QMatrix4x4()
        self.projMatrix.ortho(-2.0, 2.0, -2.0, 2.0, -0.1, 100.0)
        self.mvpMatrix = self.projMatrix * self.viewMatrix * self.modelMatrix
        self.shaderProgram = None
        self.vertexAttribIdx = 0
        self.u_MVPidx = 0
        self.u_ColorIdx = 0
        self.primType = None
        self.count = 0
        self.color = QtGui.QVector4D(1.0, 1.0, 1.0, 0.0)
        self.rendererId = None
        self.usagePattern = QtGui.QOpenGLBuffer.StaticDraw
        self.dirty = False

    def createObjects(self):
        self.shaderProgram = QtGui.QOpenGLShaderProgram()
        self.shaderProgram.create()
        self.vao.create()
        self.vbo.create()
        self.ebo.create()

    def buildShader(self):
        if not parseShader(os.path.join(SHADERPATH, 'simpleshader.glsl'), self.shaderProgram):
            print("Failed to compile shader!")
            sys.exit(1)
        else:
            self.shaderProgram.bind()
            self._cacheUniforms()

    def _cacheUniforms(self):
        self.vertexAttribIdx = self.shaderProgram.attributeLocation("position")
        self.u_MVPidx = self.shaderProgram.uniformLocation("u_mvp")
        self.u_ColorIdx = self.shaderProgram.uniformLocation("u_color")

    def bindAll(self):
        self.shaderProgram.bind()
        self.vao.bind()
        self.vbo.bind()
        self.ebo.bind()

    def setDatatype(self, vertdtype, idxdtype):
        """
        Sets datatype.
        Args:
            vertdtype: dtype as GLEnum
            idxdtype: dtype as GLEnum
        Returns: None

        """
        self.vertdtype = vertdtype
        self.idxdtype = idxdtype

    def setUsagePattern(self, pattern):
        self.usagePattern = pattern

    def allocateData(self, vertices: list, indices: list):
        self.vbo.setUsagePattern(self.usagePattern)
        self.vertices = numpy.array(vertices, dtype=numpy.float32)
        if self.vbo.bufferId():
            self.vbo.allocate(self.vertices.ctypes.data_as(ctypes.POINTER(ctypes.c_void_p)).contents,
                              sys.getsizeof(self.vertices))
            self.shaderProgram.enableAttributeArray(self.vertexAttribIdx)
            self.shaderProgram.setAttributeBuffer(self.vertexAttribIdx,  # Location of attribute in vertex shader.
                                                  self.vertdtype,  # data type of vertices.
                                                  0,  # Start location in vertices buffer.
                                                  2,  # No. of components per vertex in vertices buffer.
                                                  0)  # stride, 0 for tightly packed vertices.
        self.indices = numpy.array(indices, dtype=numpy.uint32)
        if self.ebo.bufferId():
            self.ebo.allocate(self.indices.ctypes.data_as(ctypes.POINTER(ctypes.c_void_p)).contents,
                              sys.getsizeof(self.indices))

        self.dirty = True

    def unbindAll(self):
        self.shaderProgram.release()
        self.vao.release()
        self.vbo.release()
        self.ebo.release()

    def destroyAttributes(self):
        self.vao.destroy()
        self.vbo.destroy()
        self.ebo.destroy()

    def destroy(self):
        self.unbindAll()
        self.destroyShader()
        self.destroyAttributes()

    def destroyShader(self):
        self.shaderProgram.removeAllShaders()

    def setPrimitives(self, primType):
        self.primType = primType

    def setCount(self, count):
        self.count = count

    def setColor(self, r, g, b, a):
        """
        Sets color
        Args:
            r: red 0-1
            g: green 0-1
            b: blue 0-1
            a: alpha 0-1

        Returns:

        """
        self.color = QtGui.QVector4D(r, g, b, a)

    def setViewMat(self, mat: QtGui.QMatrix4x4):
        self.viewMatrix = mat
        self.mvpMatrix = self.projMatrix * self.viewMatrix * self.modelMatrix

    def setProjMat(self, mat: QtGui.QMatrix4x4):
        self.projMatrix = mat
        self.mvpMatrix = self.projMatrix * self.viewMatrix * self.modelMatrix

    def drawCall(self, gl):
        self.shaderProgram.bind()
        self.vao.bind()
        self.shaderProgram.setUniformValue(self.u_ColorIdx, self.color)
        self.shaderProgram.setUniformValue(self.u_MVPidx, self.mvpMatrix)
        gl.glDrawElements(gl.GL_TRIANGLES, 3, self.idxdtype, None) # tri1
        self.shaderProgram.setUniformValue(self.u_ColorIdx, QtGui.QVector4D(0.0, 0.7, 0.3, 1.0))
        gl.glDrawElements(gl.GL_TRIANGLES, 3, self.idxdtype, ctypes.c_void_p(2)) # tri2.

        self.shaderProgram.release()
        self.vao.release()

class Renderer:
    """
    Manages state of graphics objects. This is responsible for drawing on viewport.
    """

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.objects = set()

    def register(self, obj: GraphicsObject):
        self.objects.add(obj)
        obj.rendererId = self.__hash__()

    def deRegister(self, obj: GraphicsObject):
        self.objects.discard(obj)
        obj.rendererId = None

    def draw(self, gl):
        """
        Call draw calls of all registered objects.
        Returns: None

        """
        eye = QtGui.QVector3D(0.0, 0.0, 2.0)
        front = QtGui.QVector3D(0.0, 0.0, -1.0)
        up = QtGui.QVector3D(0.0, 1.0, 0.0)
        view = QtGui.QMatrix4x4()
        view.lookAt(eye, front, up)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        for obj in self.objects:
            if obj.rendererId is None:
                continue
            else:
                obj.setViewMat(view)
                obj.drawCall(gl)


class GLViewport(QtWidgets.QOpenGLWidget):
    def __init__(self, parent=None):
        """
        Re-implements QOpenGLWidget.
        Args:
            parent: Optional.
        """
        super().__init__(parent)
        self.renderer = Renderer(self.width(), self.height())
        self.twotris = GraphicsObject("twotris")

    def initializeGL(self):
        defaultFmt = QtGui.QSurfaceFormat.defaultFormat()
        verProf = QtGui.QOpenGLVersionProfile(defaultFmt)
        self.m_gl = self.context().versionFunctions(verProf)
        self.m_gl.initializeOpenGLFunctions()
        print("Initialized gl")
        self.m_gl.glClearColor(64. / 255., 64. / 255., 64. / 255., 0.0)

        # two separate triangles.
        vertices = [-0.5, -0.5,  # bottom left in model's local space
                    0.5, -0.5,  # bottom right in model's local space
                    0.0, 0.0,  # common point of two tris in model's local space
                    -0.5, 0.5,  # top left in model's local space
                    0.5, 0.5]  # top right in model's local space
        indices = [0, 1, 2,
                   2, 3, 4]
        self.twotris.createObjects()
        self.twotris.buildShader()
        self.twotris.bindAll()
        self.twotris.setCount(len(vertices))
        self.twotris.setDatatype(self.m_gl.GL_FLOAT, self.m_gl.GL_UNSIGNED_INT)
        self.twotris.setUsagePattern(QtGui.QOpenGLBuffer.StaticDraw)
        self.twotris.allocateData(vertices, indices)
        self.twotris.unbindAll()
        self.twotris.setPrimitives(self.m_gl.GL_TRIANGLES)
        self.twotris.setColor(1.0, 0.0, 0.0, 0.0)

        # Register graphics objects.
        self.renderer.register(self.twotris)

    def resizeGL(self, w: int, h: int):
        self.m_gl.glViewport(0, 0, w, h)

    def paintGL(self):
        self.renderer.draw(self.m_gl)

    def flush(self):
        self.twotris.destroy()


if __name__ == '__main__':
    import sys

    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseDesktopOpenGL)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    fmt = QtGui.QSurfaceFormat.defaultFormat()
    fmt.setVersion(2, 0)  # Request 2.0, that's the minimum we can get if PyQt5 was installed with desktop OpenGL
    fmt.setSamples(4)
    fmt.setSwapInterval(1)
    QtGui.QSurfaceFormat.setDefaultFormat(fmt)

    app = QtWidgets.QApplication(sys.argv)

    window = Window(app)
    window.resize(1000, 1000)
    window.show()

    sys.exit(app.exec_())
