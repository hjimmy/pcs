name="pcs"
version="0.9.167"
fullname=$name-$version
cp -rf  source $fullname
tar -zcvf $fullname.tar.gz $fullname
cp -rf $fullname.tar.gz   ~/rpmbuild/SOURCES
cp -rf othersource/*  ~/rpmbuild/SOURCES
cp -rf *.spec ~/rpmbuild/SPECS
rpmbuild -bs --nodeps ~/rpmbuild/SPECS/$name.spec
rpmbuild -ba  ~/rpmbuild/SPECS/$name.spec
rm -rf $fullname
rm -rf $fullname.tar.gz
