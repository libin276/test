[Version]
Class=IEXPRESS
SEDVersion=3

[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=0
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=I
InstallPrompt=
DisplayLicense=
FinishMessage=MQTT Subscription Manager installation complete.
TargetName=D:\github\test\release\windows\Setup_MQTTSubscriptionManager.exe
FriendlyName=MQTT Subscription Manager Setup
AppLaunched=cmd.exe /c install.bat
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles

[SourceFiles]
SourceFiles0=D:\github\test\release\windows\build\installer

[SourceFiles0]
mqtt-subscription-manager.zip=
install.bat=
