import sys

def main():
    try:
        with open("plugins/series.py", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Find start and end of series_user_nav
        start_idx = -1
        end_idx = -1
        for i, line in enumerate(lines):
            if "async def series_user_nav(" in line:
                # The decorator is 1 line above
                start_idx = i - 1
                break
                
        if start_idx == -1:
            print("Could not find start of series_user_nav")
            return
            
        # Find the end - look for next top-level function or end of file
        # Actually we know it ends right before # ─── /serieslist
        for i in range(start_idx + 1, len(lines)):
            if lines[i].startswith("# ─── /serieslist") or lines[i].startswith("# ════════"):
                end_idx = i - 1
                break
                
        if end_idx == -1:
            print("Could not find end of series_user_nav")
            return
            
        with open("scratch_series_user_nav.py", "r", encoding="utf-8") as f:
            new_func = f.read()
            
        print(f"Replacing lines {start_idx} to {end_idx}")
        
        # Strip trailing newlines from new_func and add exactly 2
        new_func = new_func.strip() + "\n\n"
        
        new_lines = lines[:start_idx] + [new_func] + lines[end_idx:]
        
        with open("plugins/series.py", "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        print("Success.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
