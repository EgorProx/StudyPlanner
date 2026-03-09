from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1000, 700)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.mainLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.mainLayout.setObjectName("mainLayout")
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        self.menuList = QtWidgets.QListWidget(parent=self.centralwidget)
        self.menuList.setObjectName("menuList")
        self.menuList.setMaximumWidth(200)
        self.mainLayout.addWidget(self.menuList)

        self.pagesStack = QtWidgets.QStackedWidget(parent=self.centralwidget)
        self.pagesStack.setObjectName("pagesStack")
        self.mainLayout.addWidget(self.pagesStack)

        self.page_subjects = QtWidgets.QWidget()
        self.page_subjects.setObjectName("page_subjects")
        self.pagesStack.addWidget(self.page_subjects)

        self.page_settings = QtWidgets.QWidget()
        self.page_settings.setObjectName("page_settings")
        self.pagesStack.addWidget(self.page_settings)

        self.page_calendar = QtWidgets.QWidget()
        self.page_calendar.setObjectName("page_calendar")
        self.pagesStack.addWidget(self.page_calendar)

        self.page_tasks = QtWidgets.QWidget()
        self.page_tasks.setObjectName("page_tasks")
        self.pagesStack.addWidget(self.page_tasks)

        MainWindow.setCentralWidget(self.centralwidget)

        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1000, 22))
        MainWindow.setMenuBar(self.menubar)

        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Study Planner"))