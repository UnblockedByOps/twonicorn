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


class Applications(Base):
    __tablename__ = 'applications'
    application_id   = Column(Integer, primary_key=True, nullable=False)
    application_name = Column(Text, nullable=False)
    nodegroup        = Column(Text, nullable=False)
    created          = Column(TIMESTAMP, nullable=False)


class Deploys(Base):
    __tablename__ = 'deploys'
    deploy_id        = Column(Integer, primary_key=True, nullable=False)
    application_id   = Column(Integer, nullable=False,
                              ForeignKey('applications.application_id'))
    artifact_type_id = Column(Integer, nullable=False,
                              ForeignKey('artifacts.artifact_id'))
    deploy_path      = Column(Text, nullable=False)
    created          = Column(TIMESTAMP, nullable=False)
    application      = relationship("Applications", backref=backref('deploys'))


class Artifacts(Base):
    __tablename__ = 'artifacts'
    artifact_id = Column(Integer, primary_key=True, nullable=False)
    repo_id     = Column(Integer, nullable=False,
                         ForeignKey('repos.repo_id'))
    location    = Column(Text, nullable=False)
    revision    = Column(Text, nullable=False)
    branch      = Column(Text)
    valid       = Column(Integer, nullable=False)
    created     = Column(TIMESTAMP, nullable=False)


class ArtifactAssignments(Base):
    __tablename__     = 'artifact_assignments'
    artifact_assignment_id = Column(Integer, primary_key=True, nullable=False)
    deploy_id              = Column(Integer, nullable=False,
                                    ForeignKey('deploys.deploy_id'))
    env_id                 = Column(Integer, nullable=False,
                                    ForeignKey('envs.env_id'))
    lifecycle_id           = Column(Integer, nullable=False,
                                    ForeignKey('lifecycles.lifecycle_id'))
    artifact_id            = Column(Integer, nullable=False,
                                    ForeignKey('artifacts.artifact_id'))
    user                   = Column(Text, nullable=False)
    created                = Column(TIMESTAMP, nullable=False)
    deploy                 = relationship("Deploys", backref=backref('artifact_assignments'))
    artifact               = relationship("Artifacts", backref=backref('artifact_assignments'))


class ArtifactNotes(Base):
    __tablename__ = 'artifact_notes'
    artifact_note_id = Column(Integer, primary_key=True, nullable=False)
    artifact_id      = Column(Integer, nullable=False,
                              ForeignKey('artifacts.artifact_id'))
    user             = Column(Text, nullable=False)
    note             = Column(Text, nullable=False)
    created          = Column(TIMESTAMP, nullable=False)
    artifact         = relationship("Artifacts", backref=backref('notes'))


class Lifecycles(Base):
    __tablename__ = 'lifecycles'
    lifecycle_id         = Column(Integer, primary_key=True, nullable=False)
    name                 = Column(Text, nullable=False)
    artifact_assignments = relationship("ArtifactAssignments", backref=backref('lifecycle'))


class Envs(Base):
    __tablename__ = 'envs'
    env_id = Column(Integer, primary_key=True, nullable=False)
    name   = Column(Text, nullable=False)
    artifact_assignments = relationship("ArtifactAssignments", backref=backref('env'))


class Repos(Base):
    __tablename__ = 'repos'
    repo_id      = Column(Integer, primary_key=True, nullable=False)
    repo_type_id = Column(Integer, nullable=False,
                          ForeignKey('repo_types.repo_type_id'))
    name         = Column(Text, nullable=False)
    artifacts    = relationship("Artifacts", backref=backref('repos'))


class RepoTypes(Base):
    __tablename__ = 'repo_types'
    repo_type_id = Column(Integer, primary_key=True, nullable=False)
    name         = Column(Text, nullable=False)
    repos        = relationship("Repos", backref=backref('type'))


class ArtifactTypes(Base):
    __tablename__ = 'artifact_types'
    artifact_type_id = Column(Integer, primary_key=True, nullable=False)
    name             = Column(Text, nullable=False)


class RepoUrls(Base):
    __tablename__ = 'repo_urls'
    repo_url_id = Column(Integer, primary_key=True, nullable=False)
    repo_id     = Column(Integer, nullable=False,
                         ForeignKey('repos.repo_id'))
    ct_loc      = Column(Text, nullable=False)
    url         = Column(Text, nullable=False)
    repo        = relationship("Repos", backref=backref('url'))

