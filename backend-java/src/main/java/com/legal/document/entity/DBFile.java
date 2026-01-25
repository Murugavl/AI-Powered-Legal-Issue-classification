package com.legal.document.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "db_files")
public class DBFile {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String fileName;

    private String fileType;

    @Lob
    private byte[] data;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "session_id")
    private CaseSession session;

    public DBFile() {
    }

    public DBFile(String fileName, String fileType, byte[] data, CaseSession session) {
        this.fileName = fileName;
        this.fileType = fileType;
        this.data = data;
        this.session = session;
    }

    public Long getId() {
        return id;
    }

    public byte[] getData() {
        return data;
    }

    public String getFileName() {
        return fileName;
    }

    public String getFileType() {
        return fileType;
    }
}
