import datetime
import arrow
from dateutil import tz
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy import (
    Column,
    Index,
    Integer,
    Text,
    DATETIME,
    Float,
    TIMESTAMP,
    ForeignKey,
    Boolean,
    )
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    )
from zope.sqlalchemy import ZopeTransactionExtension
import re


cleanse_re = re.compile("[^A-Za-z0-9_]")
DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

def _localize_date(obj):
        utc = arrow.get(obj.created)
        zone = 'US/Pacific' # FIXME: This needs to be configurable somehow
        return  utc.to(tz.gettz(zone)).format('YYYY-MM-DD HH:mm:ss ZZ')


class Application(Base):
    __tablename__ = 'applications'
    application_id   = Column(Integer, primary_key=True, nullable=False)
    application_name = Column(Text, nullable=False)
    nodegroup        = Column(Text, nullable=False)
    created          = Column(TIMESTAMP, nullable=False)

    @hybrid_method
    def get_app_by_deploy_id(self, deploy_id):
        # Get the application
        q = DBSession.query(Application)
        q = q.join(Deploy, Application.application_id == Deploy.application_id)
        q = q.filter(Deploy.deploy_id == '%s' % deploy_id)
        return q.one()
        
    @hybrid_property
    def localize_date(self):
        local = _localize_date(self)
        return local


class Artifact(Base):
    __tablename__ = 'artifacts'
    artifact_id = Column(Integer, primary_key=True, nullable=False)
    repo_id     = Column(Integer, ForeignKey('repos.repo_id'), nullable=False)
    location    = Column(Text, nullable=False)
    revision    = Column(Text, nullable=False)
    branch      = Column(Text)
    valid       = Column(Integer, nullable=False)
    created     = Column(TIMESTAMP, nullable=False)

    @hybrid_method
    def get_promotion(self, env, deploy_id, artifact_id):
        q = DBSession.query(Artifact)
        q = q.filter(Lifecycle.name == 'current')
        q = q.filter(Deploy.deploy_id == '%s' % deploy_id)
        q = q.filter(Env.name == '%s' % env)
        q = q.filter(Artifact.artifact_id == '%s' % artifact_id)
        q = q.filter(RepoUrl.ct_loc == 'lax1')
        return q.first()

    @hybrid_property
    def localize_date(self):
        local = _localize_date(self)
        return local


class ArtifactAssignment(Base):
    __tablename__     = 'artifact_assignments'
    artifact_assignment_id = Column(Integer, primary_key=True, nullable=False)
    deploy_id              = Column(Integer, ForeignKey('deploys.deploy_id'), nullable=False)
    env_id                 = Column(Integer, ForeignKey('envs.env_id'), nullable=False)
    lifecycle_id           = Column(Integer, ForeignKey('lifecycles.lifecycle_id'), nullable=False)
    artifact_id            = Column(Integer, ForeignKey('artifacts.artifact_id'), nullable=False)
    user                   = Column(Text, nullable=False)
    created                = Column(TIMESTAMP, nullable=False)
    artifact               = relationship("Artifact", backref=backref('artifact_assignments'))

    @hybrid_property
    def pretty_url(self):
        url_location = self.artifact.repo.get_url('lax1').url + self.artifact.location
        if self.artifact.repo.name == 'gerrit':
            r = url_location.rpartition('/')
            return r[0] + r[1] + 'git/gitweb.cgi?p=' + r[2] + '.git;a=summary'
        elif self.artifact.repo.name == 'subversion':
            return url_location + '/' + self.env.name + '/?p=' + self.artifact.revision
        else:
            return url_location

    @hybrid_property
    def localize_date(self):
        local = _localize_date(self)
        return local


class ArtifactType(Base):
    __tablename__ = 'artifact_types'
    artifact_type_id = Column(Integer, primary_key=True, nullable=False)
    name             = Column(Text, nullable=False)


class Deploy(Base):
    __tablename__ = 'deploys'
    deploy_id        = Column(Integer, primary_key=True, nullable=False)
    application_id   = Column(Integer, ForeignKey('applications.application_id'), nullable=False)
    artifact_type_id = Column(Integer, ForeignKey('artifact_types.artifact_type_id'), nullable=False)
    deploy_path      = Column(Text, nullable=False)
    package_name     = Column(Text, nullable=True)
    created          = Column(TIMESTAMP, nullable=False)
    application      = relationship("Application", backref=backref('deploys'))
    artifact_assignments = relationship("ArtifactAssignment", backref=backref('deploy'),
                                          order_by=ArtifactAssignment.created.desc,
                                          lazy="dynamic")
    type = relationship("ArtifactType")

    @hybrid_method
    def get_assignment_count(self, env):
        q = self.artifact_assignments
        q = q.join(Env, ArtifactAssignment.env_id == Env.env_id)
        q = q.join(Artifact, ArtifactAssignment.artifact_id == Artifact.artifact_id)
        q = q.filter(Env.name == env)
        q = q.filter(Artifact.valid == 1)
        return q.count()

    @hybrid_method
    def get_assignments(self, env, offset, perpage):
        q = self.artifact_assignments
        q = q.join(Env, ArtifactAssignment.env_id == Env.env_id)
        q = q.join(Artifact, ArtifactAssignment.artifact_id == Artifact.artifact_id)
        q = q.filter(Env.name == env)
        q = q.filter(Artifact.valid == 1)
        return q.limit(perpage).offset(offset)

    @hybrid_method
    def get_assignment(self, env, lifecycle):
        q = self.artifact_assignments
        q = q.join(Env, ArtifactAssignment.env_id == Env.env_id)
        q = q.filter(Env.name == env)
        q = q.join(Lifecycle, ArtifactAssignment.lifecycle_id == Lifecycle.lifecycle_id)
        q = q.join(Artifact, ArtifactAssignment.artifact_id == Artifact.artifact_id)
        q = q.filter(Lifecycle.name == lifecycle)
        q = q.filter(Artifact.valid == 1)
        return q.first()


class ArtifactNote(Base):
    __tablename__ = 'artifact_notes'
    artifact_note_id = Column(Integer, primary_key=True, nullable=False)
    artifact_id      = Column(Integer, ForeignKey('artifacts.artifact_id'), nullable=False)
    user             = Column(Text, nullable=False)
    note             = Column(Text, nullable=False)
    created          = Column(TIMESTAMP, nullable=False)
    artifact         = relationship("Artifact", backref=backref('notes'))


class Lifecycle(Base):
    __tablename__ = 'lifecycles'
    lifecycle_id         = Column(Integer, primary_key=True, nullable=False)
    name                 = Column(Text, nullable=False)
    artifact_assignments = relationship("ArtifactAssignment", backref=backref('lifecycle'))


class Env(Base):
    __tablename__ = 'envs'
    env_id = Column(Integer, primary_key=True, nullable=False)
    name   = Column(Text, nullable=False)
    artifact_assignments = relationship("ArtifactAssignment", backref=backref('env'), lazy="joined")

    @hybrid_method
    def get_env_id(self, env):
        # Convert the env name to the id
        q = DBSession.query(Env)
        q = q.filter(Env.name == '%s' % env)
        return q.one()


class Repo(Base):
    __tablename__ = 'repos'
    repo_id      = Column(Integer, primary_key=True, nullable=False)
    repo_type_id = Column(Integer, ForeignKey('repo_types.repo_type_id'), nullable=False)
    name         = Column(Text, nullable=False)
    artifacts    = relationship("Artifact", backref=backref('repo'))

    @hybrid_method
    def get_url(self, ct_loc):
        for u in self.url:
            if u.ct_loc == ct_loc:
                return u
        return None


class RepoType(Base):
    __tablename__ = 'repo_types'
    repo_type_id = Column(Integer, primary_key=True, nullable=False)
    name         = Column(Text, nullable=False)
    repos        = relationship("Repo", backref=backref('type'))


class RepoUrl(Base):
    __tablename__ = 'repo_urls'
    repo_url_id = Column(Integer, primary_key=True, nullable=False)
    repo_id     = Column(Integer, ForeignKey('repos.repo_id'), nullable=False)
    ct_loc      = Column(Text, nullable=False)
    url         = Column(Text, nullable=False)
    repo        = relationship("Repo", backref=backref('url'))

