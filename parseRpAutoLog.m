function Log = parseRpAutoLog(fpath)

    % keep track of number of read lines for output
    global nparsed
    nparsed=0;
    
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
    fprintf('Going to parse %d lines: ',numel(C));
    Log=cellfun(@parseLine,C);
    fprintf('\n');
end

function S = parseLine(str)

    % print some progress info
    global nparsed
    fprintf(repmat('\b',1,length(sprintf('%d',nparsed'))));
    nparsed=nparsed+1;
    fprintf('%d',nparsed);
    
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
    