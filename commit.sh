# Commit changes
git commit -a -m "WWEMP-49"
git push

# Reinstall app
bench --site $sitename uninstall-app cheque_run --no-backup --yes
rm -rf ../../apps/cheque_run
bench get-app https://github.com/tritchot-sga/cheque_run.git
bench --site $sitename install-app cheque_run