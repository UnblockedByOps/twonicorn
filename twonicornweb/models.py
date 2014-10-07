import datetime
import arrow
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


class Application(Base):
    __tablename__ = 'applications'
    application_id   = Column(Integer, primary_key=True, nullable=False)
    application_name = Column(Text, nullable=False)
    nodegroup        = Column(Text, nullable=False)
    created          = Column(TIMESTAMP, nullable=False)


class Deploy(Base):
    __tablename__ = 'deploys'
    deploy_id        = Column(Integer, primary_key=True, nullable=False)
    application_id   = Column(Integer, ForeignKey('applications.application_id'), nullable=False)
    artifact_type_id = Column(Integer, ForeignKey('artifacts.artifact_id'), nullable=False)
    deploy_path      = Column(Text, nullable=False)
    created          = Column(TIMESTAMP, nullable=False)
    application      = relationship("Application", backref=backref('deploys'))


class Artifact(Base):
    __tablename__ = 'artifacts'
    artifact_id = Column(Integer, primary_key=True, nullable=False)
    repo_id     = Column(Integer, ForeignKey('repos.repo_id'), nullable=False)
    location    = Column(Text, nullable=False)
    revision    = Column(Text, nullable=False)
    branch      = Column(Text)
    valid       = Column(Integer, nullable=False)
    created     = Column(TIMESTAMP, nullable=False)


class ArtifactAssignment(Base):
    __tablename__     = 'artifact_assignments'
    artifact_assignment_id = Column(Integer, primary_key=True, nullable=False)
    deploy_id              = Column(Integer, ForeignKey('deploys.deploy_id'), nullable=False)
    env_id                 = Column(Integer, ForeignKey('envs.env_id'), nullable=False)
    lifecycle_id           = Column(Integer, ForeignKey('lifecycles.lifecycle_id'), nullable=False)
    artifact_id            = Column(Integer, ForeignKey('artifacts.artifact_id'), nullable=False)
    user                   = Column(Text, nullable=False)
    created                = Column(TIMESTAMP, nullable=False)
    deploy                 = relationship("Deploy", backref=backref('artifact_assignments'))
    artifact               = relationship("Artifact", backref=backref('artifact_assignments'))


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
    artifact_assignments = relationship("ArtifactAssignment", backref=backref('env'))


class Repo(Base):
    __tablename__ = 'repos'
    repo_id      = Column(Integer, primary_key=True, nullable=False)
    repo_type_id = Column(Integer, ForeignKey('repo_types.repo_type_id'), nullable=False)
    name         = Column(Text, nullable=False)
    artifacts    = relationship("Artifact", backref=backref('repos'))


class RepoType(Base):
    __tablename__ = 'repo_types'
    repo_type_id = Column(Integer, primary_key=True, nullable=False)
    name         = Column(Text, nullable=False)
    repos        = relationship("Repo", backref=backref('type'))


class ArtifactType(Base):
    __tablename__ = 'artifact_types'
    artifact_type_id = Column(Integer, primary_key=True, nullable=False)
    name             = Column(Text, nullable=False)


class RepoUrl(Base):
    __tablename__ = 'repo_urls'
    repo_url_id = Column(Integer, primary_key=True, nullable=False)
    repo_id     = Column(Integer, ForeignKey('repos.repo_id'), nullable=False)
    ct_loc      = Column(Text, nullable=False)
    url         = Column(Text, nullable=False)
    repo        = relationship("Repo", backref=backref('url'))

