import os
import sys
import subprocess
import platform
import ctypes
import win32api
import win32con
import win32process
import psutil

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def increase_page_file():
    """Increase the page file size on Windows"""
    try:
        # Get current page file size
        computer_info = win32api.GetComputerInfo()
        total_physical_memory = computer_info['TotalPhysicalMemory']
        
        # Calculate recommended page file size (1.5x RAM)
        recommended_size = int(total_physical_memory * 1.5)
        
        # Set new page file size
        subprocess.run(['wmic', 'computersystem', 'where', 'name="%computername%"', 'set', 'AutomaticManagedPagefile=False'], shell=True)
        subprocess.run(['wmic', 'pagefileset', 'where', 'name="C:\\pagefile.sys"', 'set', f'InitialSize={recommended_size},MaximumSize={recommended_size}'], shell=True)
        
        print(f"Successfully increased page file size to {recommended_size / (1024**3):.2f} GB")
        return True
    except Exception as e:
        print(f"Error increasing page file size: {str(e)}")
        return False

def install_requirements():
    """Install required Python packages"""
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("Successfully installed required packages")
        return True
    except Exception as e:
        print(f"Error installing requirements: {str(e)}")
        return False

def check_system_requirements():
    """Check if system meets minimum requirements"""
    try:
        # Check RAM (minimum 4GB)
        ram = psutil.virtual_memory().total / (1024**3)  # Convert to GB
        if ram < 4:
            print(f"Warning: Your system has {ram:.1f}GB RAM. Recommended: 4GB minimum")
            return False
        
        # Check disk space (minimum 10GB free)
        disk = psutil.disk_usage('/')
        free_space = disk.free / (1024**3)  # Convert to GB
        if free_space < 10:
            print(f"Warning: Your system has {free_space:.1f}GB free space. Recommended: 10GB minimum")
            return False
        
        print("System requirements check passed")
        return True
    except Exception as e:
        print(f"Error checking system requirements: {str(e)}")
        return False

def main():
    print("Setting up AI Mental Health Tracker...")
    
    # Check if running as admin
    if not is_admin():
        print("Please run this script as administrator to modify system settings")
        return
    
    # Check system requirements
    if not check_system_requirements():
        print("Your system may not meet the minimum requirements for optimal performance")
        proceed = input("Do you want to continue anyway? (y/n): ")
        if proceed.lower() != 'y':
            return
    
    # Increase page file size
    print("\nIncreasing page file size...")
    if increase_page_file():
        print("Page file size increased successfully")
    else:
        print("Failed to increase page file size")
        proceed = input("Do you want to continue anyway? (y/n): ")
        if proceed.lower() != 'y':
            return
    
    # Install requirements
    print("\nInstalling required packages...")
    if install_requirements():
        print("Setup completed successfully!")
        print("\nPlease restart your computer for the changes to take effect.")
        print("After restarting, you can run the application using: python main.py")
    else:
        print("Setup failed. Please check the error messages above.")

if __name__ == "__main__":
    main() 