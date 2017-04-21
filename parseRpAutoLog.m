function Log = parseRpAutoLog(fpath)

%     % keep track of number of read lines for output
%     global nparsed
%     nparsed=0;
    
    try
        fid = fopen(fpath);
        C = textscan(fid,'%s','Delimiter','\n');
        C = C{1}; % textscan returns 1-element cell array with file contents
        fclose(fid);
    catch err
        fprintf('Error reading file %s: %s\n',fpath,err.msg);
        return;
    end
    
    C(cellfun(@isempty,C))=[]; % remove empty cells
    
    %% new approach
    
    % Log line layout: 
    % 2017-04-15 00:00:08 DEBUG: [rp_auto_mod_scale ] Converted value to -3.14
    % date, warn level and module name have fixed widths
    fprintf('Going to parse %d lines...\n',numel(C));
    Sep=regexp(C,'^(?<date>[^A-Z]+)\s+(?<warnlevel>[A-Z]+)\s*\:\s*\[(?<module>[^\] ]+)\s*\]\s*(?<message>.*)\s*$','names');
    Log=cat(1,Sep{:}); % regexp places output in cell for each input cell
    clear Sep; % free memory
    
    try %#ok<TRYNC> ; use try block to return partial Log, in case something goes wrong
        fprintf('Extracting date information... ')
        FieldDate=num2cell(datenum({Log.date},'yyyy-mm-dd hh:MM:SS')); % convert date string to MATLAB-readable date number. Create cell array for deal() function
        [Log.date]=deal(FieldDate{:});
        fprintf('done\n');
        fprintf('Attempting to convert numeric values... ')
        FieldValue=str2double(cellfun(@(x,y) x(y:end),{Log.message},regexp({Log.message},'\S+$'),'UniformOutput',false)); % try converting the last word of message to a numeric value
        FieldHasvalue=~isnan(FieldValue); % indicate lines where str2double() failed, returning NaN
        fprintf('done, %d values recovered\n',nnz(FieldHasvalue));
        FieldValue=num2cell(FieldValue);
        FieldHasvalue=num2cell(FieldHasvalue);
        [Log.value]=deal(FieldValue{:});
        [Log.hasvalue]=deal(FieldHasvalue{:});
        [Log.rawmsg]=deal(C{:}); % include raw, unparsed message
    end
    
    return;
    
    %% old approach
    fprintf('Going to parse %d lines: ',numel(C));
    Log=cellfun(@parseLine,C);
    fprintf('\n');
end

function S = parseLine(str)

    % print some progress info
%     global nparsed
%     fprintf(repmat('\b',1,length(sprintf('%d',nparsed'))));
%     nparsed=nparsed+1;
%     fprintf('%d',nparsed);
    
    % Log line layout: 
    % 2017-04-15 00:00:08 DEBUG: [rp_auto_mod_scale ] Converted value to -3.14
    % date, warn level and module name have fixed widths
    S.date=datenum(str(1:19),'yyyy-mm-dd hh:MM:SS');
    S.warnlevel=str(21:25);
    S.module=strtrim(str(29:46));
    S.message=strtrim(str(49:end));
    % try to extract value -- str2double() is NaN if something goes wrong
    S.value=str2double(str(regexp(str,'\S+$'):end));
    S.hasvalue=~isnan(S.value);
    S.rawmsg=str;
    
end
    