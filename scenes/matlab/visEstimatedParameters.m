addpath '~/AncillaIP/Matlab';
%groundTruth=[1500 6000 2000];   %P1
%groundTruth=[3500 4000 1000 6000 2000 7000 2500 8000 3000 1500];
%groundTruth=[1000 4000 2000];   %P1
groundTruth=[3000, 5000]
%$groundTruth=zeros(1,10);   %P2
%groundTruth = zeros(1,16);
showStdev = 1;
nsteps=500;

prefix='cyl2-2k';
excit='pressureInc';
fem='CorLarge';
integ='Euler1';
filterType='ROUKF';
obsID = 'obs1middle';
usePCG = '0';
transform = 'project';
sdaParams='40_40_ns-5';


%obsID = 'obs2middleEnd';

%inputDir=['../assimBC/brickD_Newton3_fp1_tr1_ogrid4/ROUKFproj_OSD-3']
%inputDir=['../assimStiffness/cyl3gravity_Euler1/ROUKF_obs33_' trans '2'];
%inputDir='../assimStiffness/cyl10gravity_Euler1/ROUKF_obs120_proj5';
mainDir = [ '../assimStiffness/' prefix '_' excit '_' fem '_' integ '/' ];
inputDir = [ mainDir filterType '_' obsID '_' usePCG '_' transform '_' sdaParams ];


%inputDir='../assimStiffness/cyl3gravity_Euler1/UKFSimCorr_obs33_proj0'

estStateFile=[inputDir '/state.txt'];
estVarFile=[inputDir '/variance.txt'];

%===================================================================
nparams=size(groundTruth,2);
estState=load(estStateFile);
estVar=load(estVarFile);

if nsteps < 0
    nsteps=size(estState,1);
end

nstate=nparams;

if strcmp(transform,'abs')
    estState=abs(estState(1:nsteps,nstate-nparams+1:nstate));
    estVar=abs(estVar(1:nsteps,nstate-nparams+1:nstate));
    estStd=sqrt(estVar);
end


if strcmp(transform,'exp')
    estState=exp(estState(1:nsteps,nstate-nparams+1:nstate));
    estVar=estVar(1:nsteps,nstate-nparams+1:nstate);
    estStd=exp(sqrt(estVar));
end

if strcmp(transform,'project')
    estState=estState(1:nsteps,nstate-nparams+1:nstate);
    estVar=estVar(1:nsteps,nstate-nparams+1:nstate);
    estStd=sqrt(estVar);
end




minval=0;
maxval=max(max(estState)) + max(max(estStd));

figure; 
%axes('XLim', [1,nsteps], 'YLim', [0, 1.2*maxval]);
hold on
gtState=ones(size(estState));
cls=distinguishable_colors(nparams, 'w');

for i=1:nparams
    plot(1:nsteps, groundTruth(i)*ones(1,nsteps), 'Color', cls(i,:),'LineStyle', ':', 'LineWidth', 3);    
    if showStdev
        %errorbar(estState(:,i), estStd(:,i), 'Color', cls(i,:), 'MarkerSize', 2);
        plot(1:nsteps, estState(:,i)+estStd(:,i), 'Color', cls(i,:), 'LineStyle','--');
        plot(1:nsteps, estState(:,i)-estStd(:,i), 'Color', cls(i,:), 'LineStyle','--');
        plot(1:nsteps, estState(:,i), 'Color', cls(i,:), 'LineWidth', 2);
    else
        plot(1:nsteps, estState(:,i), 'Color', cls(i,:));
    end
    
end
title(sprintf('State  %s', [filterType ' ' integ ' ' obsID]));

return

figure; 
axes('XLim', [1,nsteps], 'YLim', [min(min(estStd)), 2*max(max(estStd))]);
hold on

for i=1:nstate
    plot(1:nsteps, estStd(:,i), 'Color', cls(i,:));
end
title(sprintf('Variance %s', filterType));









